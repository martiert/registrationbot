#!/usr/bin/env python

import argparse
import asyncio
import functools
import sys
import pymongo
from spark import Server
from register import Register


async def help(loop, spark, message):
    result = '''These are the commands I know:

register: Register if you are interested in working at Cisco
jobs: List available internship and graduate jobs
all jobs: List all available jobs
jobs <search>: search for specifics in open jobs. E.g. 'jobs software' will give you job listings relevant to software
modify: Modify registration
help: Print help text
about: Information on how this bot was made

All commands are case insensitive
'''

    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        result,
    )


async def about(loop, spark, message):
    about_text = '''Hi there, Cool that you want to look more into how I function!

The first thing you should have a look at is the developer site for Cisco Spark: https://developer.ciscospark.com/
This site contains the documentation on the Cisco Spark API, which will give you the possibility to create bots and integrations towards Cisco Spark.
It is also the way to create a new bot, get 24/7 support, find SDKs, read blogs from the developers og Cisco Spark and much more.

Being a Cisco Spark bot, I use that API. I'm written in Python, and use the ciscosparkapi python package (https://github.com/CiscoDevNet/ciscosparkapi)
to interface towards the Cisco Spark API.

Since I also need to get notified when I get a message I use aiohttp (https://aiohttp.readthedocs.io/), and Pythons asyncio library
(https://docs.python.org/3/library/asyncio-dev.html), to create a webserver that listens to these message.

To save the registered data I use mongodb (https://mongodb.com), with the pymongodb Python api (https://api.mongodb.com/python/current).
'''

    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        about_text,
    )


async def pre_message(loop, spark, message, db):
    if db.greeted.find_one({'unique_id': message.personId}):
        return

    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        'Hi! Great to see that you find Cisco interesting! I\'m and automated bot to replace the interest list you usually sign up on.',
    )
    db.greeted.insert_one({'unique_id': message.personId})


async def do_register(loop, spark, message, register):
    registration = await register.registration(message, spark, loop)
    if registration.active:
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            'Registration already ongoing',
        )
    if registration.done:
        await modify(loop, spark, message, register)
        return

    registration.active = True
    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        registration.next_question(),
    )


async def modify(loop, spark, message, register):
    registration = await register.registration(message, spark, loop)
    if not registration.done:
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            'You have to register before modifying your registration',
        )
        return

    registration.start_modify()
    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        registration.next_question(),
    )


async def abort(loop, spark, message, register):
    registration = await register.registration(message, spark, loop)
    if not registration.active:
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            'Nothing to abort',
        )
        return

    registration.abort()
    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        'Aborted',
    )
    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        registration.data(),
    )


async def default(loop, spark, message, register):
    registration = await register.registration(message, spark, loop)
    if not registration.active:
        await help(loop, spark, message)
        return

    answer = registration.answer(message.text)
    if answer:
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            answer,
        )

    await loop.run_in_executor(
        None,
        spark.messages.create,
        None,
        message.personId,
        None,
        registration.next_question(),
    )

    if registration.done:
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            registration.data(),
        )
        return


job_template = '''---
Title: {title}
Job Type: {jobtype}
Location: {location}
Date: {date}
Department: {department}
Url: {url}
'''


async def respond_with_job(loop, spark, message, jobs):
    for job in jobs:
        response = job_template.format(
            title=job['title'],
            jobtype=job['jobtype'],
            location=job['location'],
            date=job['date'],
            department=job['department'],
            url=job['url'],
        )
        await loop.run_in_executor(
            None,
            spark.messages.create,
            None,
            message.personId,
            None,
            response)


async def all_open_jobs(loop, spark, message, db):
    jobs = db.jobs.find({})
    await respond_with_job(loop, spark, message, jobs)


def search_jobs(jobs, term):
    result = []
    for job in jobs:
        if term in job['department'].lower():
            result.append(job)
        elif term in job['title'].lower():
            result.append(job)
        elif term in job['jobtype'].lower():
            result.append(job)
    return result


async def respond_default(loop, spark, message, jobs):
    result = []
    for job in jobs:
        if job['jobtype'].lower() in ['new graduate',
                                      'intern/co-op',
                                      'entry level',
                                      ]:
            result.append(job)
    await respond_with_job(loop, spark, message, result)


async def open_jobs(loop, spark, message, db):
    search_term = message.text.lower().replace('jobs', '').strip().lower()
    jobs = db.jobs.find({})

    if not search_term:
        await respond_default(loop, spark, message, jobs)
        return

    result = search_jobs(jobs, search_term)
    await respond_with_job(loop, spark, message, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port',
        '-p',
        default=3000,
    )
    parser.add_argument(
        '--webhook',
        '-w',
        required=True,
    )
    parser.add_argument(
        '--token',
        '-t',
        required=True,
    )
    parser.add_argument(
        '--database',
        '-d',
        required=True,
    )
    parser.add_argument(
        '--username',
        '-u',
        required=True,
    )
    parser.add_argument(
        '--password',
        required=True,
    )

    args = parser.parse_args()

    mongodb = pymongo.MongoClient()
    db = mongodb[args.database]
    db.authenticate(args.username, args.password)

    register = Register(db)

    loop = asyncio.get_event_loop()
    server = Server({'port': args.port,
                     'webhook': args.webhook,
                     'token': args.token,
                     },
                    loop)

    server.pre_message(functools.partial(pre_message, db=db))
    server.listen('^register$', functools.partial(do_register, register=register))
    server.listen('^modify$', functools.partial(modify, register=register))
    server.listen('^abort$', functools.partial(abort, register=register))
    server.listen('^all jobs', functools.partial(all_open_jobs, db=db))
    server.listen('^jobs', functools.partial(open_jobs, db=db))
    server.listen('^about$', about)
    server.default_message(functools.partial(default, register=register))

    loop.run_until_complete(server.setup())

    print('======== Bot Ready ========')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except:
        print(sys.exc_info())
    finally:
        loop.run_until_complete(server.cleanup())


if __name__ == '__main__':
    main()
