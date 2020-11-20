import sqlite3
from dateutil import parser
from tomo import tomo_day, noww
from flask import Flask, request, jsonify, session
from flask.helpers import make_response
from werkzeug.security import check_password_hash, generate_password_hash
import random

SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

app = Flask(__name__)
app.config['SECRET_KEY'] = 'c48a640f477b68a551af2ee98a59cea62a102ca683d62691de372e3ee2676ee9'

conn = sqlite3.connect('tododatabase.sqlite', check_same_thread=False)
cur = conn.cursor()

try :
    cur.executescript(
    '''
    CREATE TABLE users (
        id                INTEGER NOT NULL PRIMARY KEY, 
        public_id         INTEGER NOT NULL UNIQUE, 
        username          VARCHAR(20) UNIQUE, 
        firstname         VARCHAR(15) NOT NULL, 
        lastname          VARCHAR(15) NOT NULL, 
        password          VARCHAR NOT NULL, 
        emailaddress      VARCHAR(30) NOT NULL UNIQUE  
    );

    CREATE TABLE tasks(
        id                INTEGER  PRIMARY KEY UNIQUE,
        user_id           INTEGER,
        title             VARCHAR,
        date              DATETIME NOT NULL,
        description       VARCHAR
    );

    CREATE TABLE status (
        id                INTEGER NOT NULL  PRIMARY KEY , 
        status_id         INTEGER, 
        task_id           INTEGER, 
        user_id           INTEGER, 
        completed         BOOLEAN NOT NULL, 
        d_repeats         BOOLEAN NOT NULL, 
        m_repeats         BOOLEAN NOT NULL, 
        y_repeats         BOOLEAN NOT NULL, 
        deadline          DATETIME, 
        remainders        VARCHAR
    );

    CREATE TABLE priority (
        task_id           INTEGER UNIQUE,
        red               BOOLEAN,
        yellow            BOOLEAN,
        green             BOOLEAN
    );

    CREATE TABLE project (
        p_id              INTEGER PRIMARY KEY UNIQUE,
        task_id           INTEGER UNIQUE,
        personal          BOOLEAN,
        shopping          BOOLEAN,
        family            BOOLEAN,
        work              BOOLEAN

    )
    '''
    )
    conn.commit()

except sqlite3.OperationalError as e:
    print(e)
    conn.commit()


@app.route('/register', methods=['POST'])
def post_register():
    data = request.get_json(force=True)
    cur = conn.cursor()
    hashed_password = generate_password_hash(data['password'], method='sha256')

    if not data :
        return jsonify({
            'message' : 'No data provided'
        }), 401
    
    cur.execute('''
    SELECT * FROM users WHERE username = ( ? ) 
    ''', (data['username'], ))
    user = cur.fetchone()
    if user :
        return jsonify({
            'message' : 'Username already taken..'
        })

    cur.execute('''
    SELECT * FROM users WHERE emailaddress = ( ? ) 
    ''', (data['emailaddress'],))
    user = cur.fetchone()
    if user :
        return jsonify({
            'message' : 'Email address already taken..'
        })

    public_id = random.randint(1, 50000)

    if (data['firstname'] == '') or (data['username'] == '') or (data['lastname'] == ''):
        return jsonify({
            'message' : 'Do not enter empty strings in firstname, lastname and username'
        }), 401
    
    cur.execute('''
    INSERT OR IGNORE INTO users (public_id, firstname, lastname, emailaddress, password, username)
    VALUES ( ? , ? , ? , ? , ? , ? )
    ''', (int(public_id), data['firstname'], data['lastname'], data['emailaddress'], hashed_password, data['username']))

    conn.commit()
    return jsonify({
        'Status' : f"Added the user {data['username']}..",
        'public_id' : f'{public_id}'
    })

@app.route('/', methods=['GET'])
def home():

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401


    cur = conn.cursor()
    cur.execute('''
    SELECT * FROM users
    ''')
    users = cur.fetchall()

    output = []

# [(1, 42762, 'vital', 'vital', 'k', 'sha256$IS3Kw0dI$7c93a652bba19d133db37b10c0e21ae26e2234a45843625341f3638392b9538b', 'vital@gmail.com')]

    for user in users :
        home = {}
        home['id'] = user[0]
        home['public_id'] = user[1]
        home['username'] = user[2]
        home['emailaddress'] = user[-1]
        output.append(home)

    return jsonify({'home':{
        'Users':output
        }})

@app.route('/login', methods=['POST'])
def signin() :

    data = request.get_json(force=True)
    cur = conn.cursor()

    if not data :
        return jsonify({
            'message' : 'No data provided'
        })

    cur.execute('''
    SELECT * FROM users WHERE emailaddress = ( ? ) 
    ''', (data['emailaddress'],))
    user = cur.fetchone()

    if not user:
        return jsonify({
            'Message' : "No such user."
        })

    if check_password_hash(user[5], data['password']) :
        session['emailaddress'] = data['emailaddress']
        session['public_id'] = user[1]

        return jsonify({
            'Message' : 'You are logged in',
        }),200

    return jsonify({
        'Message' : "Emailaddress or Password does not match"
    })


@app.route('/logout', methods=['GET'])
def user() :
    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    session.pop('public_id')
    session.pop('emailaddress')

    return make_response('logged out user', 200)



@app.route('/task', methods=['POST'])
def post_task():

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    cur = conn.cursor()
    data = request.get_json(force=True)

    if not 'date' in data :
        data['date'] = noww()

    cur.execute('''
    INSERT OR IGNORE INTO tasks (title, description, user_id, date)
    VALUES ( ? , ? , ? , ? )''', (data['title'], data['description'], session['public_id'], data['date']))
    conn.commit()
    
    cur.execute(
    '''
    SELECT * FROM tasks WHERE title = ? AND description = ? AND user_id = ? AND date = ?
    ''', (data['title'], data['description'], session['public_id'], data['date']))
    task = cur.fetchone()

    if not 'repeats' in data :
        if not 'd_repeats' in data['repeats']['d_repeats'] :
            data['d_repeats'] = False
        if not 'm_repeats' in data['repeats']['m_repeats'] :
            data['m_repeats'] = False
        if not 'y_repeats' in data['repeats']['y_repeats'] :
            data['y_repeats'] = False

    if not 'deadline' in data :
        data['deadline'] = tomo_day()
    if not 'completed' in data :
        data['completed'] = False
    if not 'remainders' in data :
        data['remainders'] = 'Remainder for you'

    if 'priority' in data :
        if not 'red' in data['priority'] :
            data['priority']['red'] = False
        if not 'yellow' in data['priority'] :
            data['priority']['yellow'] = False
        if not 'green' in data['priority'] :
            data['priority']['green'] = False

    if 'project' in data :
        if not 'personal' in data['project'] :
            data['project']['personal'] = False
        if not 'family' in data['project'] :
            data['project']['family'] = False
        if not 'work' in data['project'] :
            data['project']['work'] = False
        if not 'shopping' in data['project'] :
            data['project']['shopping'] = False
    
    cur.execute(
    '''
    INSERT INTO priority (task_id, red, yellow, green)
    VALUES (? , ? , ? , ? )
    ''', (task[0], data['priority']['red'], data['priority']['yellow'], data['priority']['green']))
    conn.commit()

    cur.execute(
    '''
    INSERT INTO project (task_id, personal, family, work, shopping)
    VALUES (?, ?, ?, ?, ? )
    ''', (task[0], data['project']['personal'], data['project']['family'], data['project']['work'], data['project']['shopping']))

    cur.execute(
    '''
    INSERT INTO status (status_id, task_id, user_id, deadline, d_repeats, m_repeats, y_repeats, remainders, completed)
    VALUES ( ? , ? , ? , ? , ? , ? , ? , ? , ?)
    ''', (int(random.randint(1, 50000)), task[0], session['public_id'], data['deadline'], data['repeats']['d_repeats'], data['repeats']['m_repeats'], data['repeats']['y_repeats'], data['remainders'], data['completed']))

    conn.commit()

    return jsonify({'message' : 'task created'})

@app.route('/status', methods=['GET'])
def task_status() :

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401
    
    cur = conn.cursor()
    cur.execute(
    '''
    SELECT * FROM tasks WHERE user_id = ?
    ''', (session['public_id'], ))
    user_task = cur.fetchall()

    cur.execute(
    '''
    SELECT * FROM status WHERE user_id = ? 
    ''', (session['public_id'], ))
    user_status = cur.fetchall()


    output = []
    for status,task in zip(user_status, user_task) :
        status_dict = {}
        repeats = {}
        project_dict = {}
        priority_dict = {}
        status_dict['date'] = task[3]
        cur.execute(
        '''
        SELECT * FROM project WHERE task_id = ? 
        ''', (task[0], ))
        project = cur.fetchone()

        cur.execute(
        '''
        SELECT * FROM priority WHERE task_id = ? 
        ''', (task[0], ))
        priority = cur.fetchone()

        status_dict['discription'] = task[-1]
        status_dict['task_id'] = status[2]
        status_dict['status_id'] = status[1]
        status_dict['user_id'] = status[3]
        status_dict['completed'] = status[4]

        if status :
            repeats['d_repeats'] = status[5]
            repeats['m_repeats'] = status[6]
            repeats['y_repeats'] = status[7]
        status_dict['repeats'] = repeats

        if priority :
            priority_dict['red'] = priority[1]
            priority_dict['yellow'] = priority[2]
            priority_dict['green'] = priority[3]
        status_dict['priority'] = priority_dict

        if project :
            project_dict['personal'] = project[2]
            project_dict['shopping'] = project[3]
            project_dict['family'] = project[-2]
            project_dict['work'] = project[-1]
        status_dict['project'] = project_dict

        status_dict['deadline'] = status[-2]
        status_dict['remainders'] = status[-1]
        status_dict['title'] = task[2]
        

        if noww() >= parser.parse(status_dict['deadline']) :
            status_dict['remind_alert'] = True
        else :
            status_dict['remind_alert'] = False
        output.append(status_dict)
    
    return jsonify({
        'Profile' : output
    })


@app.route('/task', methods=['GET'])
def get_tasks():

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401


    cur = conn.cursor()
    cur.execute('''
    SELECT * FROM tasks WHERE user_id = ?
    ''', (session['public_id'], ))
    tasks = cur.fetchall()

    output = []
    for task in tasks :
        t_dict = {}
        t_dict['id'] = task[0]
        t_dict['user_id'] = task[1]
        t_dict['title'] = task[2]
        t_dict['date'] = task[3]
        t_dict['description'] = task[-1]
        output.append(t_dict)

    return jsonify({'home':{
        'Tasks':output
        }})

@app.route('/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }), 401


    cur = conn.cursor()
    cur.execute(
    '''
    SELECT * FROM tasks WHERE id = ? AND user_id = ?
    ''', (task_id, session['public_id']))
    task = cur.fetchone()

    if not task :
        return jsonify({
            'message' : 'no task found!'
        }), 401

    cur.execute(
    '''
    SELECT * FROM status WHERE task_id = ? AND user_id = ?
    ''', (task_id, session['public_id']))
    status = cur.fetchone()

    if not status :
        return jsonify({
            'message' : 'no status assosiated to the task found!'
        }), 401
    
    cur.execute(
    '''
    DELETE FROM tasks WHERE id = ? AND user_id = ?
    ''', (task_id, session['public_id']))

    cur.execute(
    '''
    DELETE FROM status WHERE task_id = ? AND user_id = ?
    ''', (task_id, session['public_id']))
    conn.commit()

    cur.execute(
        '''
        DELETE FROM priority WHERE task_id = ?
        ''', (task_id, )
    )
    conn.commit()

    cur.execute(
        '''
        DELETE FROM project WHERE task_id = ?
        ''',(task_id, )
    )
    conn.commit()
    
    return jsonify({
        'message' : 'Task item deleted!'
    })

@app.route('/task/<int:task_id>', methods=['PUT'])
def complete_task(task_id):

    if not ('public_id' in session ):
        return jsonify({
            'Message' : 'Login to access this page'
        }),401

    data = request.get_json(force=True)
    
    cur = conn.cursor()
    cur.execute(
    '''
    SELECT * FROM tasks WHERE id = ? AND user_id = ? 
    ''', (task_id, session['public_id']))
    task = cur.fetchone()

    if not task :
        return jsonify({
            'message' : 'No task found!!',
        }), 401

    cur.execute(
    '''
    SELECT * FROM status WHERE task_id = ? AND user_id = ? 
    ''', (task_id, session['public_id']))
    status = cur.fetchone()

    if not status :
        return jsonify({
        'message' : 'no status assosiated to the task found!'
    }), 401


    if 'description' in data :
        cur.execute('''UPDATE tasks SET description = ? 
        WHERE id = ? 
        ''', (data['description'], task[0]))
        conn.commit()
        # print('note')

    if 'title' in data :
        cur.execute(
    '''
    UPDATE tasks SET title = ? 
    WHERE id = ?
    ''', (data['title'], task[0]))
        conn.commit()
        # print('title')

    if 'completed' in data :
        cur.execute(
    '''
    UPDATE status SET completed = ? 
    WHERE task_id = ?
    ''', (data['completed'], task[0]))
        conn.commit()
        # print('completed')

    if 'deadline' in data :
        cur.execute(
    '''
    UPDATE status SET deadline = ? 
    WHERE task_id = ?
    ''', (data['deadline'], task[0]))
        conn.commit()
        # print('deadline')

    if 'd_repeats' in data['repeats'] :
        cur.execute(
    '''
    UPDATE status SET d_repeats = ? 
    WHERE task_id = ?
    ''', (data['repeats']['d_repeats'], task[0]))
        conn.commit()
        # print('d repeats')

    if 'm_repeats' in data['repeats'] :
        cur.execute(
    '''
    UPDATE status SET m_repeats = ? 
    WHERE task_id = ?
    ''', (data['repeats']['m_repeats'], task[0]))
        conn.commit()
        # print('m repeats')

    if 'y_repeats' in data['repeats']:
        cur.execute(
    '''
    UPDATE status SET y_repeats = ? 
    WHERE task_id = ?
    ''', (data['repeats']['y_repeats'], task[0]))
        conn.commit()
        # print('y repeats')

    if 'remainders' in data:
        cur.execute(
    '''
    UPDATE status SET remainders = ? 
    WHERE task_id = ?
    ''', (data['remainders'],task[0]))
        conn.commit()
        # print('remainders')

    if 'red' in data['priority'] :
        cur.execute(
        '''
        UPDATE priority SET red = ? 
        WHERE task_id = ?
        ''', (data['priority']['red'], task[0]))
        conn.commit()

    if 'yellow' in data['priority'] :
        cur.execute(
        '''
        UPDATE priority SET yellow = ? 
        WHERE task_id = ?
        ''', (data['priority']['yellow'], task[0]))
        conn.commit()

    if 'green' in data['priority'] :
        cur.execute(
        '''
        UPDATE priority SET green = ? 
        WHERE task_id = ?
        ''', (data['priority']['green'], task[0]))
        conn.commit()

    if 'personal' in data['project'] :
        cur.execute(
        '''
        UPDATE project SET personal = ? 
        WHERE  task_id = ? 
        ''', (data['project']['personal'], task[0]))
        conn.commit()

    if 'shopping' in data['project'] :
        cur.execute(
        '''
        UPDATE project SET shopping = ? 
        WHERE task_id = ?
        ''', (data['project']['shopping'], task[0]))
        conn.commit()

    if 'family' in data['project'] :
        cur.execute(
        '''
        UPDATE project SET family = ? 
        WHERE task_id = ?
        ''', (data['project']['family'], task[0]))
        conn.commit()

    if 'family' in data['project'] :
        cur.execute(
        '''
        UPDATE project SET family = ? 
        WHERE task_id = ?
        ''', (data['project']['family'], task[0]))
        conn.commit()
    
    return jsonify({
        'Task' : "task is updated!!!",
        'Status' : 'status is updated'
    })


if __name__ == "__main__":
    app.run(debug=True)