class Nothing:
    def __init__(self, parent):
        self._parent = parent

    def question(self):
        pass

    def answer(self, message):
        pass


class Finished:
    def __init__(self, parent):
        self._parent = parent

    def question(self):
        answer = '''Thank you for registering.

You will soon be contacted with more information.'''
        self._parent.finished()
        return answer

    def answer(self, message):
        return Nothing(self)


class JobType:
    def __init__(self, parent, nextState=Finished):
        self._parent = parent
        self._nextState = nextState

    def question(self):
        return 'Are you looking for a summer internship or a permanent job? <permanent/internship>'

    def answer(self, message):
        if message.strip().lower() not in ['permanent', 'internship']:
            return None
        self._parent.job_type(message)
        return self._nextState(self._parent)


class DoneStudying:
    def __init__(self, parent, nextState=JobType):
        self._parent = parent
        self._nextState = nextState

    def question(self):
        return 'When are you finished with your studies?'

    def answer(self, message):
        self._parent.done_studying(message)
        return self._nextState(self._parent)


class CurrentStudy:
    def __init__(self, parent, nextState=DoneStudying):
        self._parent = parent
        self._nextState = nextState

    def question(self):
        return 'What are you studying?'

    def answer(self, message):
        self._parent.study(message)
        return self._nextState(self._parent)


class SetName:
    def __init__(self, parent, nextState=DoneStudying):
        self._parent = parent
        self._nextState = nextState

    def question(self):
        return 'What is your name?'

    def answer(self, message):
        self._parent.name(message)
        return self._nextState(self._parent)


class SetEmail:
    def __init__(self, parent, nextState=DoneStudying):
        self._parent = parent
        self._nextState = nextState

    def question(self):
        return 'What is your email address?'

    def answer(self, message):
        self._parent.email(message)
        return self._nextState(self._parent)


class Modify:
    def __init__(self, parent):
        self._parent = parent

    def question(self):
        return '''What do you want to modify?

1) name
2) email
3) What you are studying
4) When you are done studying
5) What type of job you are interested in

<1/2/3/4/5>
'''

    def answer(self, message):
        answers = {1: SetName,
                   2: SetEmail,
                   3: CurrentStudy,
                   4: DoneStudying,
                   5: JobType,
                   }
        try:
            number = int(message.strip())
        except ValueError:
            return None

        if number not in answers.keys():
            return None
        return answers[number](self._parent, nextState=Finished)


class Registration:
    def __init__(self, unique_id, email, name, db):
        self._db = db
        self.set_data(unique_id, name, email)

    def set_data(self, unique_id, name, email):
        self._data = {'unique_id': unique_id,
                      'name': name,
                      'email': email,
                      }

        self._state = CurrentStudy(self)
        self.active = False
        self.done = False

        data = self._db.registered.find_one({'unique_id': unique_id})
        if data:
            self._data = data
            self.done = True
            self._state = Nothing(self)

    def __repr__(self):
        return '''Name: {}
Email: {}
'''.format(self._name, self._email)

    def next_question(self):
        return self._state.question()

    def answer(self, message):
        state = self._state.answer(message)
        if not state:
            return 'Answer \'{}\' not accepted'.format(message)
        self._state = state

    def study(self, studying):
        self._data['studying'] = studying

    def done_studying(self, done):
        self._data['done'] = done

    def job_type(self, jobtype):
        self._data['type'] = jobtype

    def name(self, name):
        self._data['name'] = name

    def email(self, email):
        self._data['email'] = email

    def finished(self):
        self._db.registered.update_one(
            {'unique_id': self._data['unique_id']},
            {'$set': self._data},
            upsert=True)
        self.active = False
        self.done = True

    def start_modify(self):
        self.active = True
        self.done = False
        self._state = Modify(self)

    def abort(self):
        self.set_data(
            self._data['unique_id'],
            self._data['name'],
            self._data['email'])

    def data(self):
        return '''Name: {}
Email: {}
Studying: {}
Finished studying: {}
Type of work: {}
'''.format(self._data['name'],
           self._data['email'],
           self._data['studying'],
           self._data['done'],
           self._data['type'],
           )


class Register:
    def __init__(self, db):
        self._registrations = {}
        self._db = db

    async def registration(self, message, spark, loop):
        id = message.personId
        if message.personId in self._registrations.keys():
            return self._registrations[id]

        person_info = await loop.run_in_executor(
            None,
            spark.people.get,
            id)

        email = person_info.emails[0]
        name = person_info.displayName
        registration = Registration(id, email, name, self._db)
        self._registrations[message.personId] = registration
        return registration
