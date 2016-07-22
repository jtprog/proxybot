from telebot import types as types
import bson
import base64

import config


def to_python(value):
    try:
        return bson.ObjectId(base64.urlsafe_b64decode(value))
    except (bson.errors.InvalidId, ValueError, TypeError):
        raise ValueError


def to_url(value):
    return base64.urlsafe_b64encode(value.binary)


def short_id(value):
    oid = bson.ObjectId(str(value))
    time = int(oid.generation_time.timestamp()) * 1000
    counter = int(str(oid)[-6:], 16)
    counter = int(str(counter)[-3:], 10)
    time += counter
    s = base64.urlsafe_b64encode(time.to_bytes(6, 'big'))
    s = s[1:]
    s = s[::-1]
    return s


# adds Dictionaryable behavior and marks models which can be stored in db
class Model(types.Dictionaryable):
    def to_dic(self):
        d = {}
        for k, v in vars(self).items():
            if isinstance(v, Model):
                d[k] = v.to_dic()
            elif not str(k).startswith('_'):
                if str(k) == 'id':
                    k = '_id'
                d[k] = v
        return d


# Represents User and adds extra fields to telepot's class
class User(Model, types.User):
    def __init__(self, *args, **kwargs):
        if not args:
            args = (
                int(kwargs.get('_id') or kwargs.get('id')),
                kwargs['first_name'],
                kwargs.get('last_name'),
                kwargs.get('username'),
            )
        self.blocked = kwargs.get('blocked')
        super().__init__(*args)

    def update(self, data):
        assert int(self.id) == int(data.id)
        self.first_name = data.first_name
        self.last_name = data.last_name
        self.username = data.username

    def __format__(self, format_spec):
        if format_spec == 'short':
            return '''/u{id} {username} {first_name} {blocked}'''.format(
                id=self.id,
                username='@' + self.username if self.username else '',
                first_name=self.first_name,
                blocked='BLOCKED' if self.blocked else ''
            )
        if format_spec == 'full':
            return '''\
Id: {id}
Username: {username}
First name: {first}
Last name: {last}
{blocked}'''.format(
                id=self.id,
                first=self.first_name,
                last=self.last_name or '_Not_set_',
                username='@' + self.username if self.username else '_Not_set_',
                blocked='BLOCKED' if self.blocked else ''
            )

        return self.__format__('short')  # default to short if no format_spec



# Represents message, add ObjectId
class Message(Model, types.Message):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = bson.ObjectId()

    def to_dic(self):
        d = dict()
        d['_id'] = self.id
        d['tg_id'] = self.message_id
        d['short_id'] = short_id(self.id)
        d['from_user'] = self.from_user.id
        if self.from_user.id == config.my_id and self.reply_to_message:
            d['with'] = self.reply_to_message.from_user.id
        else:
            d['with'] = self.from_user.id

        if self.text:
            d['text'] = self.text
        else:
            d['text'] = 'Non text message: /m' + short_id(self.id)
        return d


# Just adds Dictionaryable to chat
class Chat(Model, types.Chat):
    pass


# Replaces classes in telepot.types
def replace_classes():
    types.User = User
    types.Message = Message
    types.Chat = Chat