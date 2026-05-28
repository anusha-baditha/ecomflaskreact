from flask import Flask,request,jsonify,session,make_response,url_for
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_session import Session
from flask_bcrypt import Bcrypt
from mysql.connector import connection

from cmail import send_mail 
from otp import genotp
import os
import uuid
import razorpay
from werkzeug.utils import secure_filename
from stoken import endata,dndata
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib import colors

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.pagesizes import A4

from reportlab.platypus.flowables import HRFlowable
from datetime import timedelta


import re
import os
app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['PREFERRED_URL_SCHEME'] = 'https'
app.permanent_session_lifetime=timedelta(days=1)
# enable react connection
CORS(
    app,
    supports_credentials=True
)

bcrypt=Bcrypt(app)

# session config
app.secret_key='code123'

app.config['SESSION_TYPE']='filesystem'
app.config['SESSION_COOKIE_SECURE']=True
app.config['SESSION_COOKIE_HTTPONLY']=True
app.config['SESSION_COOKIE_SAMESITE']='None'

Session(app)

# upload folder
BASE_DIR=os.path.abspath(
    os.path.dirname(__file__)
)

UPLOAD_FOLDER=os.path.join(
    BASE_DIR,
    'static',
    'uploads'
)

app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)
ALLOWED_EXTENSIONS={"png",'jpg','gif','webp','jpeg'}
MAX_CONTENT_LENGTH=6 *1024*1024 #6MB

# mysql connection
mydb=connection.MySQLConnection(
    user='root',
    password='admin',
    host='localhost',
    database='ecom22db'
)

# razorpay
client=razorpay.Client(
    auth=(
        "rzp_test_SHy3zlzWZXNg3W",
        "B67PBLrrvi1BP38vgyIEdOHg"
    )
)

@app.route('/')
def home():

    return jsonify({

        'status':'success',

        'message':'BUYROUTE Backend Running'
    })


@app.route(
    '/api/products',
    methods=['GET']
)
def index():

    cursor = None

    try:

        # Reconnect automatically if MySQL connection is lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)

        cursor.execute(
            '''
            SELECT
                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img
            FROM items
            '''
        )

        allitems_data = cursor.fetchall()

        products = []

        for item in allitems_data:

            products.append({

                'itemid': item[0],

                'itemname': item[1],

                'item_desc': item[2],

                'item_about': item[3],

                'price': float(item[4]),

                'quantity': item[5],

                'category': item[6],

                'image': url_for(
                    'static',
                    filename=f'uploads/{item[7]}',
                    _external=True
                )
            })

        return jsonify({

            'status': 'success',

            'products': products
        })

    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500

    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/register',
    methods=['POST']
)
def admincreate():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        admin_name = data.get(
            'username',
            ''
        ).strip()

        admin_email = data.get(
            'useremail',
            ''
        ).strip()

        admin_address = data.get(
            'useraddress',
            ''
        ).strip()

        admin_password = data.get(
            'userpassword',
            ''
        ).strip()

        admin_agree = data.get('useragree')


        # validations
        if not admin_name:

            return jsonify({

                'status': 'failed',

                'message': 'Username required'

            }), 400


        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(
            email_pattern,
            admin_email
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid email'

            }), 400


        if len(admin_password) < 6:

            return jsonify({

                'status': 'failed',

                'message': 'Password too short'

            }), 400


        # hash password
        hashed_password = bcrypt.generate_password_hash(
            admin_password
        ).decode('utf-8')


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM admindata
            WHERE admin_email=%s
            ''',
            [admin_email]
        )

        email_count = cursor.fetchone()[0]


        if email_count > 0:

            return jsonify({

                'status': 'failed',

                'message': 'Email already exists'

            }), 400


        gotp = genotp()


        admindata = {

            'admin_username': admin_name,

            'admin_useremail': admin_email,

            'admin_address': admin_address,

            'admin_userpassword': hashed_password,

            'admin_agree': admin_agree,

            'admin_otp': gotp
        }


        subject = 'Admin Registration Verification'


        body = f'''
Hello Admin,

Your OTP is: {gotp}

This OTP is valid for 5 minutes.

BUYROUTE Team
'''


        send_mail(

            to=admin_email,

            subject=subject,

            body=body
        )


        token = endata(admindata)


        return jsonify({

            'status': 'success',

            'message': 'OTP sent successfully',

            'token': token
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/verify-otp',
    methods=['POST']
)
def adminotpverify():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        userotp = data.get('otp')

        token = data.get('token')


        if not userotp or not token:

            return jsonify({

                'status': 'failed',

                'message': 'OTP and token required'

            }), 400


        # decrypt token safely
        try:

            admin_details = dndata(token)

        except Exception:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid or expired token'

            }), 400


        # otp validation
        if str(userotp) != str(
            admin_details['admin_otp']
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid OTP'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        # email recheck
        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM admindata
            WHERE admin_email=%s
            ''',
            [admin_details['admin_useremail']]
        )

        email_exists = cursor.fetchone()[0]


        if email_exists > 0:

            return jsonify({

                'status': 'failed',

                'message': 'Email already registered'

            }), 400


        # already hashed password
        hashed_password = admin_details[
            'admin_userpassword'
        ]


        cursor.execute(
            '''
            INSERT INTO admindata(
                adminid,
                adminname,
                admin_email,
                admin_password,
                admin_address,
                admin_agree
            )
            VALUES(
                uuid_to_bin(uuid()),
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ''',
            [
                admin_details['admin_username'],

                admin_details['admin_useremail'],

                hashed_password,

                admin_details['admin_address'],

                admin_details['admin_agree']
            ]
        )

        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'Admin Registered Successfully'
        })


    except Exception as e:

        mydb.rollback()

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/login',
    methods=['POST']
)
def adminlogin():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        login_email = data.get(
            'email',
            ''
        ).strip()

        login_password = data.get(
            'password',
            ''
        ).strip()


        if not login_email or not login_password:

            return jsonify({

                'status': 'failed',

                'message': 'Email and password required'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT
                BIN_TO_UUID(adminid),
                adminname,
                admin_email,
                admin_password
            FROM admindata
            WHERE admin_email=%s
            ''',
            [login_email]
        )

        admin_data = cursor.fetchone()


        if not admin_data:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid Email'

            }), 404


        adminid = admin_data[0]

        adminname = admin_data[1]

        adminemail = admin_data[2]

        stored_password = admin_data[3]


        if not bcrypt.check_password_hash(
            stored_password,
            login_password
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid Password'

            }), 401


        session.permanent = True

        session['adminid'] = adminid

        session['adminemail'] = adminemail


        return jsonify({

            'status': 'success',

            'message': 'Login Successful',

            'admin': {

                'adminid': adminid,

                'adminname': adminname,

                'adminemail': adminemail
            }
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/dashboard',
    methods=['GET']
)
def admindashboard():

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # success response
        return jsonify({

            'status': 'success',

            'message': 'Welcome Admin',

            'admin': {

                'adminid': session.get('adminid'),

                'adminemail': session.get('adminemail')
            }
        })


    except Exception as e:

        print("DASHBOARD ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500



def allowed_file(filename: str) -> bool:

    return (

        "." in filename and

        filename.rsplit('.', 1)[1].lower()

        in ALLOWED_EXTENSIONS
    )
@app.route(
    '/api/admin/add-item',
    methods=['POST']
)
def additem():

    save_path = None

    cursor = None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        item_name = request.form.get(
            'title',
            ''
        ).strip()

        item_description = request.form.get(
            'Description',
            ''
        ).strip()

        item_about = request.form.get(
            'About_item',
            ''
        ).strip()

        item_quantity = request.form.get(
            'quantity',
            ''
        ).strip()

        item_price = request.form.get(
            'price',
            ''
        ).strip()

        item_category = request.form.get(
            'category',
            ''
        ).strip()


        # validations
        if not item_name:

            return jsonify({

                'status': 'failed',

                'message': 'Item title required'

            }), 400


        try:

            item_price = float(item_price)

            item_quantity = int(item_quantity)

        except ValueError:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid price or quantity'

            }), 400


        item_filedata = request.files.get('file')


        if not item_filedata:

            return jsonify({

                'status': 'failed',

                'message': 'Image required'

            }), 400


        filename = item_filedata.filename


        if not allowed_file(filename):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid file type'

            }), 400


        if not item_filedata.mimetype.startswith(
            'image/'
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid image'

            }), 400


        orig_secure = secure_filename(filename)

        ext = os.path.splitext(orig_secure)[1]


        filename = genotp() + ext


        save_path = os.path.join(

            app.config['UPLOAD_FOLDER'],

            filename
        )


        item_filedata.save(save_path)


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        adminid = session.get('adminid')


        cursor.execute(
            '''
            INSERT INTO items(

                itemid,
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                added_by,
                item_img

            )

            VALUES(

                uuid_to_bin(uuid()),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                uuid_to_bin(%s),
                %s
            )
            ''',
            [

                item_name,

                item_description,

                item_about,

                item_price,

                item_quantity,

                item_category,

                adminid,

                filename
            ]
        )

        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'Item Added Successfully',

            'image': url_for(

                'static',

                filename=f'uploads/{filename}',

                _external=True
            )
        })


    except Exception as e:

        mydb.rollback()

        print("ADD ITEM ERROR:", str(e))

        # cleanup uploaded file
        if save_path and os.path.exists(save_path):

            os.remove(save_path)

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/admin/items',
    methods=['GET']
)
def viewallitems():

    cursor = None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        adminid = session.get('adminid')


        # fetch items
        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            FROM items

            WHERE added_by=uuid_to_bin(%s)
            ''',
            [adminid]
        )


        allitems_data = cursor.fetchall()


        products = []


        for item in allitems_data:

            products.append({

                'itemid': item[0],

                'itemname': item[1],

                'item_desc': item[2],

                'item_about': item[3],

                'price': float(item[4]),

                'quantity': item[5],

                'category': item[6],

                'image': url_for(

                    'static',

                    filename=f'uploads/{item[7]}',

                    _external=True
                )
            })


        return jsonify({

            'status': 'success',

            'products': products
        })


    except Exception as e:

        print("VIEW ITEMS ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/item/<itemid>',
    methods=['GET']
)
def viewitem(itemid):

    cursor = None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # validate uuid
        try:

            uuid.UUID(itemid)

        except ValueError:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid item id'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        adminid = session.get('adminid')


        # fetch single item
        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            FROM items

            WHERE
                added_by=UUID_TO_BIN(%s)
            AND
                itemid=UUID_TO_BIN(%s)
            ''',
            [adminid, itemid]
        )


        item_data = cursor.fetchone()


        if not item_data:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        product = {

            'itemid': item_data[0],

            'itemname': item_data[1],

            'item_desc': item_data[2],

            'item_about': item_data[3],

            'price': float(item_data[4]),

            'quantity': item_data[5],

            'category': item_data[6],

            'image': url_for(

                'static',

                filename=f'uploads/{item_data[7]}',

                _external=True
            )
        }


        return jsonify({

            'status': 'success',

            'product': product
        })


    except Exception as e:

        print("VIEW ITEM ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/admin/delete-item/<itemid>',
    methods=['DELETE']
)
def deleteitem(itemid):

    cursor = None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # validate uuid
        try:

            uuid.UUID(itemid)

        except ValueError:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid item id'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        adminid = session.get('adminid')


        # fetch item
        cursor.execute(
            '''
            SELECT item_img

            FROM items

            WHERE
                itemid=UUID_TO_BIN(%s)
            AND
                added_by=UUID_TO_BIN(%s)
            ''',
            [itemid, adminid]
        )

        item_data = cursor.fetchone()


        if not item_data:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        image_name = item_data[0]


        remove_path = os.path.join(

            app.config['UPLOAD_FOLDER'],

            image_name
        )


        # delete database first
        cursor.execute(
            '''
            DELETE FROM items

            WHERE
                itemid=UUID_TO_BIN(%s)
            AND
                added_by=UUID_TO_BIN(%s)
            ''',
            [itemid, adminid]
        )

        mydb.commit()


        # delete image after db success
        if os.path.exists(remove_path):

            os.remove(remove_path)


        return jsonify({

            'status': 'success',

            'message': 'Item Deleted Successfully'
        })


    except Exception as e:

        mydb.rollback()

        print("DELETE ITEM ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/update-item/<itemid>',
    methods=['PUT']
)
def updateitem(itemid):

    new_image_path = None
    old_image_path = None
    cursor = None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # validate uuid
        try:

            uuid.UUID(itemid)

        except ValueError:

            return jsonify({

                'status':'failed',

                'message':'Invalid item id'
            }),400


        # receive form data
        updateditem_name=request.form.get(
            'title',
            ''
        ).strip()

        updateditem_description=request.form.get(
            'Description',
            ''
        ).strip()

        updateditem_about=request.form.get(
            'About_item',
            ''
        ).strip()

        updateditem_quantity=request.form.get(
            'quantity',
            ''
        ).strip()

        updateditem_price=request.form.get(
            'price',
            ''
        ).strip()

        updateditem_category=request.form.get(
            'category',
            ''
        ).strip()


        # validations
        if not updateditem_name:

            return jsonify({

                'status':'failed',

                'message':'Title required'
            }),400


        try:

            updateditem_price=float(
                updateditem_price
            )

            updateditem_quantity=int(
                updateditem_quantity
            )

        except ValueError:

            return jsonify({

                'status':'failed',

                'message':'Invalid price or quantity'
            }),400


        mydb.ping(reconnect=True)


        cursor=mydb.cursor(buffered=True)


        adminid=session.get('adminid')


        # fetch existing item
        cursor.execute(
            '''
            SELECT

                item_img

            FROM items

            WHERE
                added_by=UUID_TO_BIN(%s)
            AND
                itemid=UUID_TO_BIN(%s)
            ''',
            [adminid,itemid]
        )

        item_data=cursor.fetchone()


        if not item_data:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        old_image=item_data[0]

        filename=old_image


        # receive image
        updateditem_filedata=request.files.get(
            'file'
        )


        # new image upload
        if updateditem_filedata:

            uploaded_filename=updateditem_filedata.filename


            # extension validation
            if not allowed_file(uploaded_filename):

                return jsonify({

                    'status':'failed',

                    'message':'Only png,jpg,jpeg,webp,gif allowed'
                }),400


            # mimetype validation
            if not updateditem_filedata.mimetype.startswith(
                'image/'
            ):

                return jsonify({

                    'status':'failed',

                    'message':'Invalid image type'
                }),400


            # secure filename
            orig_secure=secure_filename(
                uploaded_filename
            )

            ext=os.path.splitext(
                orig_secure
            )[1]


            # generate unique filename
            filename=genotp()+ext


            # save new image
            new_image_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                filename
            )


            updateditem_filedata.save(
                new_image_path
            )


            # old image path
            old_image_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                old_image
            )


        # update database
        cursor.execute(
            '''
            UPDATE items

            SET

                itemname=%s,
                item_desc=%s,
                item_about=%s,
                price=%s,
                quantity=%s,
                category=%s,
                item_img=%s

            WHERE
                added_by=UUID_TO_BIN(%s)
            AND
                itemid=UUID_TO_BIN(%s)
            ''',
            [

                updateditem_name,

                updateditem_description,

                updateditem_about,

                updateditem_price,

                updateditem_quantity,

                updateditem_category,

                filename,

                adminid,

                itemid
            ]
        )


        mydb.commit()

        cursor.close()


        # delete old image AFTER db success
        if (
            updateditem_filedata
            and old_image_path
            and os.path.exists(old_image_path)
        ):

            os.remove(old_image_path)


        return jsonify({

            'status':'success',

            'message':'Item Updated Successfully',

            'image':url_for(

                'static',

                filename=f'uploads/{filename}',

                _external=True
            )
        })


    except Exception as e:
        mydb.rollback()

        print("UPDATE ITEM ERROR:", str(e))

        # remove newly uploaded image if db fails
        if (
            new_image_path
            and os.path.exists(new_image_path)
        ):

            os.remove(new_image_path)


        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/admin/profile-update',
    methods=['PUT']
)
def adminprofileupdate():

    new_image_path=None
    old_image_path=None

    try:

        # session validation
        if 'adminid' not in session:

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # receive form data
        updated_adminname=request.form.get(
            'adminname',
            ''
        ).strip()

        updated_adminaddress=request.form.get(
            'address',
            ''
        ).strip()

        updated_adminphone=request.form.get(
            'ph_no',
            ''
        ).strip()


        # validations
        if not updated_adminname:

            return jsonify({

                'status':'failed',

                'message':'Admin name required'
            }),400


        mydb.ping(reconnect=True)

        cursor=mydb.cursor(buffered=True)


        adminid=session.get('adminid')


        # fetch admin details
        cursor.execute(
            '''
            SELECT

                adminid,
                adminname,
                admin_phoneno,
                admin_address,
                admin_imgdata

            FROM admindata

            WHERE adminid=UUID_TO_BIN(%s)
            ''',
            [adminid]
        )

        admin_data=cursor.fetchone()


        if not admin_data:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        # existing image
        old_image=admin_data[4]


        # receive file
        updated_adminprofile=request.files.get(
            'file'
        )


        # default old image
        filename=old_image


        # if new image uploaded
        if updated_adminprofile:

            uploaded_filename=updated_adminprofile.filename


            # extension validation
            if not allowed_file(uploaded_filename):

                return jsonify({

                    'status':'failed',

                    'message':'Only png,jpg,jpeg,webp,gif allowed'
                }),400


            # mimetype validation
            if not updated_adminprofile.mimetype.startswith(
                'image/'
            ):

                return jsonify({

                    'status':'failed',

                    'message':'Invalid image type'
                }),400


            # secure filename
            orig_secure=secure_filename(
                uploaded_filename
            )

            ext=os.path.splitext(
                orig_secure
            )[1]


            # generate unique filename
            filename=genotp()+ext


            # save new image
            new_image_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                filename
            )


            updated_adminprofile.save(
                new_image_path
            )


            # old image path
            if old_image:

                old_image_path=os.path.join(

                    app.config['UPLOAD_FOLDER'],

                    old_image
                )


        # update database
        cursor.execute(
            '''
            UPDATE admindata

            SET

                adminname=%s,
                admin_address=%s,
                admin_phoneno=%s,
                admin_imgdata=%s

            WHERE adminid=UUID_TO_BIN(%s)
            ''',
            [

                updated_adminname,

                updated_adminaddress,

                updated_adminphone,

                filename,

                adminid
            ]
        )


        mydb.commit()

        cursor.close()


        # delete old image AFTER db success
        if (
            updated_adminprofile
            and old_image_path
            and os.path.exists(old_image_path)
        ):

            os.remove(old_image_path)


        return jsonify({

            'status':'success',

            'message':'Admin Profile Updated Successfully',

            'profile_image':url_for(

                'static',

                filename=f'uploads/{filename}',

                _external=True
            )
        })


    except Exception as e:
        mydb.rollback()

        print("UPDATE Admin ERROR:", str(e))

        # remove newly uploaded image if db fails
        if (
            new_image_path
            and os.path.exists(new_image_path)
        ):

            os.remove(new_image_path)


        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/admin/logout',
    methods=['POST']
)
def adminlogout():

    try:

        # check session
        if 'adminid' not in session:

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # clear complete session
        session.clear()


        return jsonify({

            'status':'success',

            'message':'Logout Successful'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500

@app.route(
    '/api/user/register',
    methods=['POST']
)
def usercreate():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        user_name = data.get(
            'username',
            ''
        ).strip()

        user_email = data.get(
            'useremail',
            ''
        ).strip()

        user_address = data.get(
            'useraddress',
            ''
        ).strip()

        user_password = data.get(
            'userpassword',
            ''
        ).strip()

        user_phone = data.get(
            'userphone',
            ''
        ).strip()

        user_gender = data.get(
            'usergender',
            ''
        ).strip()


        # validations
        if not user_name:

            return jsonify({

                'status': 'failed',

                'message': 'Username required'

            }), 400


        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(
            email_pattern,
            user_email
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid email'

            }), 400


        if len(user_password) < 6:

            return jsonify({

                'status': 'failed',

                'message': 'Password too short'

            }), 400


        # hash password
        hashed_password = bcrypt.generate_password_hash(
            user_password
        ).decode('utf-8')


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM userdata
            WHERE useremail=%s
            ''',
            [user_email]
        )

        email_count = cursor.fetchone()[0]


        if email_count > 0:

            return jsonify({

                'status': 'failed',

                'message': 'Email already exists'

            }), 400


        gotp = genotp()


        userdata = {

            'user_username': user_name,

            'user_useremail': user_email,

            'user_address': user_address,

            'user_userpassword': hashed_password,

            'user_phone': user_phone,

            'user_gender': user_gender,

            'user_otp': gotp
        }


        subject = 'User Registration Verification'


        body = f'''
Hello User,

Your OTP is: {gotp}

This OTP is valid for 5 minutes.

BUYROUTE Team
'''


        send_mail(

            to=user_email,

            subject=subject,

            body=body
        )


        token = endata(userdata)


        return jsonify({

            'status': 'success',

            'message': 'OTP sent successfully',

            'token': token
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/user/verify-otp',
    methods=['POST']
)
def userotpverify():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        userotp = data.get('otp')

        token = data.get('token')


        if not userotp or not token:

            return jsonify({

                'status': 'failed',

                'message': 'OTP and token required'

            }), 400


        # decrypt token safely
        try:

            user_details = dndata(token)

        except Exception:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid or expired token'

            }), 400


        # otp validation
        if str(userotp) != str(
            user_details['user_otp']
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid OTP'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        # email recheck
        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM userdata
            WHERE useremail=%s
            ''',
            [user_details['user_useremail']]
        )

        email_exists = cursor.fetchone()[0]


        if email_exists > 0:

            return jsonify({

                'status': 'failed',

                'message': 'Email already registered'

            }), 400


        # already hashed password
        hashed_password = user_details[
            'user_userpassword'
        ]


        cursor.execute(
            '''
            INSERT INTO userdata(
                userid,
                username,
                useremail,
                password,
                useraddress,
                userphone,
                usergender
            )
            VALUES(
                uuid_to_bin(uuid()),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ''',
            [
                user_details['user_username'],

                user_details['user_useremail'],

                hashed_password,

                user_details['user_address'],

                user_details['user_phone'],

                user_details['user_gender']
            ]
        )

        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'User Registered Successfully'
        })


    except Exception as e:

        mydb.rollback()

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/user/login',
    methods=['POST']
)
def userlogin():

    cursor = None

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        login_email = data.get(
            'email',
            ''
        ).strip()

        login_password = data.get(
            'password',
            ''
        ).strip()


        if not login_email or not login_password:

            return jsonify({

                'status': 'failed',

                'message': 'Email and password required'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT
                BIN_TO_UUID(userid),
                username,
                useremail,
                password
            FROM userdata
            WHERE useremail=%s
            ''',
            [login_email]
        )

        user_data = cursor.fetchone()


        if not user_data:

            return jsonify({

                'status': 'failed',

                'message': 'Invalid Email'

            }), 404


        userid = user_data[0]

        username = user_data[1]

        useremail = user_data[2]

        stored_password = user_data[3]


        if not bcrypt.check_password_hash(
            stored_password,
            login_password
        ):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid Password'

            }), 401


        session.permanent = True

        session['userid'] = userid

        session['useremail'] = useremail


        # optional cart session
        if not session.get(useremail):

            session[useremail] = {}


        return jsonify({

            'status': 'success',

            'message': 'Login Successful',

            'user': {

                'userid': userid,

                'username': username,

                'useremail': useremail
            }
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/user/logout',
    methods=['POST']
)
def userlogout():

    try:

        # check session
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # remove user session
        session.pop('userid', None)

        session.pop('useremail', None)


        return jsonify({

            'status': 'success',

            'message': 'Logout successful'
        })


    except Exception as e:

        print("LOGOUT ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500
@app.route(
    '/api/cart/add',
    methods=['POST']
)
def addcart():

    cursor = None

    try:

        # login check
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        itemid = data.get('itemid')

        quantity = int(
            data.get('quantity', 1)
        )


        if not itemid:

            return jsonify({

                'status': 'failed',

                'message': 'Item ID required'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # check item exists
        cursor.execute(
            '''
            SELECT quantity

            FROM items

            WHERE itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item = cursor.fetchone()


        if not item:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        available_stock = item[0]


        # stock validation
        if quantity > available_stock:

            return jsonify({

                'status': 'failed',

                'message': 'Insufficient stock'

            }), 400


        # already in cart?
        cursor.execute(
            '''
            SELECT quantity

            FROM cart

            WHERE userid=uuid_to_bin(%s)
            AND itemid=uuid_to_bin(%s)
            ''',
            [userid, itemid]
        )

        existing_cart = cursor.fetchone()


        # update quantity
        if existing_cart:

            new_quantity = existing_cart[0] + quantity


            if new_quantity > available_stock:

                return jsonify({

                    'status': 'failed',

                    'message': 'Stock limit exceeded'

                }), 400


            cursor.execute(
                '''
                UPDATE cart

                SET quantity=%s

                WHERE userid=uuid_to_bin(%s)
                AND itemid=uuid_to_bin(%s)
                ''',
                [new_quantity, userid, itemid]
            )

            message = 'Cart quantity updated'


        # insert new item
        else:

            cursor.execute(
                '''
                INSERT INTO cart(

                    cartid,
                    userid,
                    itemid,
                    quantity

                )

                VALUES(

                    uuid_to_bin(uuid()),
                    uuid_to_bin(%s),
                    uuid_to_bin(%s),
                    %s
                )
                ''',
                [userid, itemid, quantity]
            )

            message = 'Item added to cart'


        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': message
        })


    except Exception as e:

        mydb.rollback()

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/cart/view',
    methods=['GET']
)
def viewcart():

    cursor = None

    try:

        # login check
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # fetch cart items
        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(i.itemid),

                i.itemname,

                i.price,

                c.quantity,

                i.category,

                i.item_img

            FROM cart c

            JOIN items i

            ON c.itemid=i.itemid

            WHERE c.userid=uuid_to_bin(%s)
            ''',
            [userid]
        )

        cart_items = cursor.fetchall()


        # empty cart
        if not cart_items:

            return jsonify({

                'status': 'failed',

                'message': 'Cart is empty'
            }), 404


        subtotal = 0

        items_data = []


        for item in cart_items:

            itemid = item[0]

            item_name = item[1]

            item_price = float(item[2])

            item_quantity = int(item[3])

            item_category = item[4]

            item_imgname = item[5]


            total = item_price * item_quantity

            subtotal += total


            image_url = url_for(

                'static',

                filename=f'uploads/{item_imgname}',

                _external=True
            )


            items_data.append({

                'itemid': itemid,

                'itemname': item_name,

                'price': item_price,

                'quantity': item_quantity,

                'category': item_category,

                'image': image_url,

                'total': total
            })


        delivery = 40

        tax = round(subtotal * 0.05, 2)

        grand_total = subtotal + delivery + tax


        return jsonify({

            'status': 'success',

            'cart_items': items_data,

            'summary': {

                'subtotal': subtotal,

                'delivery': delivery,

                'tax': tax,

                'grand_total': grand_total
            }
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/cart/update',
    methods=['PUT']
)
def updatecart():

    cursor = None

    try:

        # login check
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        itemid = data.get('itemid')

        updated_quantity = int(
            data.get('quantity', 0)
        )


        # quantity validation
        if updated_quantity <= 0:

            return jsonify({

                'status': 'failed',

                'message': 'Quantity must be greater than 0'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # check cart item exists
        cursor.execute(
            '''
            SELECT quantity

            FROM cart

            WHERE userid=uuid_to_bin(%s)
            AND itemid=uuid_to_bin(%s)
            ''',
            [userid, itemid]
        )

        cart_item = cursor.fetchone()


        if not cart_item:

            return jsonify({

                'status': 'failed',

                'message': 'Item not in cart'

            }), 404


        # stock validation
        cursor.execute(
            '''
            SELECT quantity

            FROM items

            WHERE itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        stock_item = cursor.fetchone()


        if not stock_item:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        available_stock = stock_item[0]


        if updated_quantity > available_stock:

            return jsonify({

                'status': 'failed',

                'message': 'Insufficient stock'

            }), 400


        # update quantity
        cursor.execute(
            '''
            UPDATE cart

            SET quantity=%s

            WHERE userid=uuid_to_bin(%s)
            AND itemid=uuid_to_bin(%s)
            ''',
            [updated_quantity, userid, itemid]
        )


        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'Cart updated successfully'
        })


    except Exception as e:

        mydb.rollback()

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/cart/remove/<itemid>',
    methods=['DELETE']
)
def removecart(itemid):

    cursor = None

    try:

        # login check
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # check item exists in cart
        cursor.execute(
            '''
            SELECT quantity

            FROM cart

            WHERE userid=uuid_to_bin(%s)
            AND itemid=uuid_to_bin(%s)
            ''',
            [userid, itemid]
        )

        cart_item = cursor.fetchone()


        if not cart_item:

            return jsonify({

                'status': 'failed',

                'message': 'Item not in cart'

            }), 404


        # remove cart item
        cursor.execute(
            '''
            DELETE FROM cart

            WHERE userid=uuid_to_bin(%s)
            AND itemid=uuid_to_bin(%s)
            ''',
            [userid, itemid]
        )


        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'Item removed from cart'
        })


    except Exception as e:

        mydb.rollback()

        print("MYSQL ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/payment/create-order',
    methods=['POST']
)
def pay_cart():

    cursor = None

    try:

        # login validation
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        data = request.get_json()

        payment_type = data.get(
            'type',
            'cart'
        )


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # CART PAYMENT
        if payment_type == 'cart':

            cursor.execute(
                '''
                SELECT

                    BIN_TO_UUID(i.itemid),

                    i.itemname,

                    i.price,

                    c.quantity,

                    i.category,

                    i.item_img

                FROM cart c

                JOIN items i

                ON c.itemid=i.itemid

                WHERE c.userid=uuid_to_bin(%s)
                ''',
                [userid]
            )

            cart_items = cursor.fetchall()


        # SINGLE BUY
        else:

            itemid = data.get('itemid')

            quantity = int(
                data.get('quantity', 1)
            )


            cursor.execute(
                '''
                SELECT

                    BIN_TO_UUID(itemid),

                    itemname,

                    price,

                    category,

                    item_img,

                    quantity

                FROM items

                WHERE itemid=uuid_to_bin(%s)
                ''',
                [itemid]
            )

            item = cursor.fetchone()


            if not item:

                return jsonify({

                    'status': 'failed',

                    'message': 'Item not found'

                }), 404


            available_stock = item[5]


            if quantity > available_stock:

                return jsonify({

                    'status': 'failed',

                    'message': 'Insufficient stock'

                }), 400


            cart_items = [(
                item[0],
                item[1],
                item[2],
                quantity,
                item[3],
                item[4]
            )]


        # empty cart check
        if not cart_items:

            return jsonify({

                'status': 'failed',

                'message': 'Cart is empty'

            }), 404


        subtotal = 0

        items_data = []


        for item in cart_items:

            itemid = item[0]

            item_name = item[1]

            item_price = float(item[2])

            item_quantity = int(item[3])

            item_category = item[4]

            item_img = item[5]


            amount = item_price * item_quantity

            subtotal += amount


            image_url = url_for(

                'static',

                filename=f'uploads/{item_img}',

                _external=True
            )


            items_data.append({

                'itemid': itemid,

                'itemname': item_name,

                'price': item_price,

                'quantity': item_quantity,

                'category': item_category,

                'image': image_url,

                'amount': amount
            })


        delivery = 40

        tax = round(subtotal * 0.05, 2)

        grand_total = subtotal + delivery + tax


        razorpay_amount = int(
            grand_total * 100
        )


        # create razorpay order
        order = client.order.create({

            "amount": razorpay_amount,

            "currency": "INR",

            "receipt": str(userid),

            "payment_capture": 1
        })


        return jsonify({

            'status': 'success',

            'order': {

                'order_id': order['id'],

                'amount': order['amount'],

                'currency': order['currency']
            },

            'cart_items': items_data,

            'summary': {

                'subtotal': subtotal,

                'delivery': delivery,

                'tax': tax,

                'grand_total': grand_total
            },

            'razorpay_key': 'rzp_test_SHy3zlzWZXNg3W'
        })


    except Exception as e:

        print("PAYMENT ERROR:", str(e))

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()
@app.route(
    '/api/payment/verify',
    methods=['POST']
)
def verify_payment():

    cursor = None

    try:

        data = request.get_json()


        # -----------------------------------
        # GET FRONTEND DATA
        # -----------------------------------

        payment_id = data.get(
            'razorpay_payment_id'
        )

        order_id = data.get(
            'razorpay_order_id'
        )

        signature = data.get(
            'razorpay_signature'
        )

        mode = data.get(
            'mode',
            'cart'
        )


        # -----------------------------------
        # VERIFY SIGNATURE
        # -----------------------------------

        params_dict = {

            'razorpay_order_id': order_id,

            'razorpay_payment_id': payment_id,

            'razorpay_signature': signature
        }


        try:

            client.utility.verify_payment_signature(
                params_dict
            )

        except Exception as e:

            print(e)

            return jsonify({

                'status': 'failed',

                'message': 'Payment verification failed'

            }), 400


        # -----------------------------------
        # LOGIN VALIDATION
        # -----------------------------------

        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # -----------------------------------
        # GET CART ITEMS
        # -----------------------------------

        if mode == 'cart':

            cursor.execute(
                '''
                SELECT

                    BIN_TO_UUID(i.itemid),

                    i.itemname,

                    i.price,

                    c.quantity,

                    i.category,

                    i.item_img

                FROM cart c

                JOIN items i

                ON c.itemid=i.itemid

                WHERE c.userid=uuid_to_bin(%s)
                ''',
                [userid]
            )

            cart_items = cursor.fetchall()


        # -----------------------------------
        # SINGLE BUY
        # -----------------------------------

        else:

            itemid = data.get('itemid')

            quantity = int(
                data.get('quantity', 1)
            )


            cursor.execute(
                '''
                SELECT

                    BIN_TO_UUID(itemid),

                    itemname,

                    price,

                    category,

                    item_img,

                    quantity

                FROM items

                WHERE itemid=uuid_to_bin(%s)
                ''',
                [itemid]
            )

            item = cursor.fetchone()


            if not item:

                return jsonify({

                    'status': 'failed',

                    'message': 'Item not found'

                }), 404


            available_stock = item[5]


            if quantity > available_stock:

                return jsonify({

                    'status': 'failed',

                    'message': 'Insufficient stock'

                }), 400


            cart_items = [(
                item[0],
                item[1],
                item[2],
                quantity,
                item[3],
                item[4]
            )]


        # -----------------------------------
        # EMPTY CHECK
        # -----------------------------------

        if not cart_items:

            return jsonify({

                'status': 'failed',

                'message': 'Cart empty'

            }), 404


        # -----------------------------------
        # CALCULATE TOTAL
        # -----------------------------------

        subtotal = 0


        for item in cart_items:

            item_price = float(item[2])

            item_quantity = int(item[3])

            subtotal += (
                item_price * item_quantity
            )


        delivery = 40

        tax = round(subtotal * 0.05, 2)

        grand_total = subtotal + delivery + tax


        # -----------------------------------
        # STORE ORDER
        # -----------------------------------

        cursor.execute(
            '''
            INSERT INTO orders(

                razorpay_ordid,

                razorpay_payment,

                userid,

                total_amount,

                delivery,

                tax,

                grand_total

            )

            VALUES(

                %s,%s,uuid_to_bin(%s),%s,%s,%s,%s
            )
            ''',

            [

                order_id,

                payment_id,

                userid,

                subtotal,

                delivery,

                tax,

                grand_total
            ]
        )


        order_table_id = cursor.lastrowid


        # -----------------------------------
        # STORE ORDER ITEMS
        # -----------------------------------

        insert_item_query = '''
        INSERT INTO order_items(

            orderid,

            itemid,

            item_name,

            item_price,

            item_quantity,

            subtotal,

            item_category,

            item_filename

        )

        VALUES(

            %s,
            uuid_to_bin(%s),
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        '''


        ordered_items = []


        for item in cart_items:

            itemid = item[0]

            item_name = item[1]

            item_price = float(item[2])

            item_quantity = int(item[3])

            item_category = item[4]

            item_img = item[5]


            amount = item_price * item_quantity


            cursor.execute(

                insert_item_query,

                [

                    order_table_id,

                    str(itemid),

                    item_name,

                    item_price,

                    item_quantity,

                    amount,

                    item_category,

                    item_img
                ]
            )


            # reduce stock
            cursor.execute(
                '''
                UPDATE items

                SET quantity = quantity - %s

                WHERE itemid=uuid_to_bin(%s)
                ''',
                [item_quantity, itemid]
            )


            ordered_items.append({

                'itemid': itemid,

                'itemname': item_name,

                'price': item_price,

                'quantity': item_quantity,

                'subtotal': amount
            })


        # -----------------------------------
        # CLEAR CART
        # -----------------------------------

        if mode == 'cart':

            cursor.execute(

                '''
                DELETE FROM cart

                WHERE userid=uuid_to_bin(%s)
                ''',

                [userid]
            )


        mydb.commit()


        # -----------------------------------
        # SUCCESS RESPONSE
        # -----------------------------------

        return jsonify({

            'status': 'success',

            'message': 'Payment verified successfully',

            'payment': {

                'payment_id': payment_id,

                'order_id': order_id
            },

            'summary': {

                'subtotal': subtotal,

                'delivery': delivery,

                'tax': tax,

                'grand_total': grand_total
            },

            'ordered_items': ordered_items
        })


    except Exception as e:

        mydb.rollback()

        print(e)

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/myorders',
    methods=['GET']
)
def myorders():

    cursor = None

    try:

        # check login
        if 'userid' not in session:

            return jsonify({

                "status": "failed",

                "message": "Please login first"

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # fetch all orders
        cursor.execute(
            '''
            SELECT

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            FROM orders

            WHERE userid=uuid_to_bin(%s)

            ORDER BY created_at DESC
            ''',
            [userid]
        )

        orders = cursor.fetchall()


        all_orders = []


        for order in orders:

            orderid = order[0]


            # fetch ordered items
            cursor.execute(
                '''
                SELECT

                    BIN_TO_UUID(itemid),

                    item_name,

                    item_price,

                    item_quantity,

                    subtotal,

                    item_category,

                    item_filename

                FROM order_items

                WHERE orderid=%s
                ''',
                [orderid]
            )

            items = cursor.fetchall()


            order_items = []


            for item in items:

                image_url = url_for(

                    'static',

                    filename=f'uploads/{item[6]}',

                    _external=True
                )


                order_items.append({

                    'itemid': item[0],

                    'itemname': item[1],

                    'price': float(item[2]),

                    'quantity': item[3],

                    'subtotal': float(item[4]),

                    'category': item[5],

                    'image': image_url
                })


            all_orders.append({

                "orderid": orderid,

                "razorpay_order_id": order[1],

                "razorpay_payment_id": order[2],

                "subtotal": float(order[3]),

                "delivery": float(order[4]),

                "tax": float(order[5]),

                "grand_total": float(order[6]),

                "created_at": str(order[7]),

                "items": order_items
            })


        return jsonify({

            "status": "success",

            "orders": all_orders
        })


    except Exception as e:

        print("MYSQL ERROR:", str(e))

        return jsonify({

            "status": "failed",

            "message": "Could not fetch orders"

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/orders/<ordid>',
    methods=['GET']
)
def myorder_details(ordid):

    cursor = None

    try:

        # ---------------- LOGIN CHECK ----------------
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # ---------------- GET ORDER DETAILS ----------------
        cursor.execute(
            '''
            SELECT

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            FROM orders

            WHERE userid=uuid_to_bin(%s)
            AND orderid=%s
            ''',
            [userid, ordid]
        )

        order_data = cursor.fetchone()


        if not order_data:

            return jsonify({

                'status': 'failed',

                'message': 'Order not found'

            }), 404


        # ---------------- GET ORDER ITEMS ----------------
        cursor.execute(
            '''
            SELECT

                order_detailsid,
                orderid,
                BIN_TO_UUID(itemid),
                item_name,
                item_price,
                item_quantity,
                subtotal,
                item_category,
                item_filename

            FROM order_items

            WHERE orderid=%s
            ''',
            [ordid]
        )

        orders_itemsdata = cursor.fetchall()


        # ---------------- FORMAT ORDER ----------------
        order_json = {

            'orderid': order_data[0],

            'razorpay_order_id': order_data[1],

            'razorpay_payment_id': order_data[2],

            'total_amount': float(order_data[3]),

            'delivery': float(order_data[4]),

            'tax': float(order_data[5]),

            'grand_total': float(order_data[6]),

            'created_at': str(order_data[7])
        }


        # ---------------- FORMAT ITEMS ----------------
        items_json = []


        for item in orders_itemsdata:

            image_url = url_for(

                'static',

                filename=f'uploads/{item[8]}',

                _external=True
            )


            items_json.append({

                'order_details_id': item[0],

                'order_id': item[1],

                'itemid': item[2],

                'item_name': item[3],

                'item_price': float(item[4]),

                'item_quantity': int(item[5]),

                'subtotal': float(item[6]),

                'item_category': item[7],

                'item_image': image_url
            })


        # ---------------- FINAL RESPONSE ----------------
        return jsonify({

            'status': 'success',

            'order': order_json,

            'items': items_json
        })


    except Exception as e:

        print(f'Order Details Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/buy-now',
    methods=['POST']
)
def buy_now():

    cursor = None

    try:

        # ---------------- LOGIN CHECK ----------------
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        itemid = data.get('itemid')

        quantity = int(
            data.get('quantity', 1)
        )


        if not itemid:

            return jsonify({

                'status': 'failed',

                'message': 'Item ID required'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        # ---------------- FETCH ITEM ----------------
        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            FROM items

            WHERE itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item_data = cursor.fetchone()


        # ---------------- ITEM CHECK ----------------
        if not item_data:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        available_stock = item_data[5]


        # ---------------- STOCK VALIDATION ----------------
        if quantity > available_stock:

            return jsonify({

                'status': 'failed',

                'message': 'Insufficient stock'

            }), 400


        image_url = url_for(

            'static',

            filename=f'uploads/{item_data[7]}',

            _external=True
        )


        # ---------------- STORE TEMP BUY NOW SESSION ----------------
        session['single_buy'] = {

            itemid: [

                item_data[1],      # item name

                quantity,          # quantity

                item_data[4],      # price

                item_data[5],      # stock

                item_data[6],      # category

                item_data[7]       # image
            ]
        }

        session.modified = True


        # ---------------- RESPONSE ----------------
        return jsonify({

            'status': 'success',

            'message': 'Single buy item stored successfully',

            'payment_type': 'single',

            'item': {

                'itemid': item_data[0],

                'itemname': item_data[1],

                'description': item_data[2],

                'about': item_data[3],

                'price': float(item_data[4]),

                'quantity': quantity,

                'stock': item_data[5],

                'category': item_data[6],

                'image': image_url
            },

            # frontend will use this
            'next_url': '/api/payment/create-order'
        })


    except Exception as e:

        print(f'Buy Now Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/invoice/<int:ord_id>',
    methods=['GET']
)
def get_invoice(ord_id):

    cursor = None

    try:

        # ---------------- LOGIN CHECK ----------------
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # ---------------- GET ORDER ----------------
        cursor.execute(
            '''
            SELECT

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            FROM orders

            WHERE userid=uuid_to_bin(%s)
            AND orderid=%s
            ''',
            [userid, ord_id]
        )

        order_data = cursor.fetchone()


        if not order_data:

            return jsonify({

                'status': 'failed',

                'message': 'Order not found'

            }), 404


        # ---------------- GET ORDER ITEMS ----------------
        cursor.execute(
            '''
            SELECT

                item_name,
                item_price,
                item_quantity,
                subtotal,
                item_category

            FROM order_items

            WHERE orderid=%s
            ''',
            [ord_id]
        )

        order_items = cursor.fetchall()


        # ---------------- CREATE PDF BUFFER ----------------
        pdf_buffer = BytesIO()


        # ---------------- CREATE DOCUMENT ----------------
        doc = SimpleDocTemplate(

            pdf_buffer,

            pagesize=A4,

            rightMargin=30,

            leftMargin=30,

            topMargin=30,

            bottomMargin=20
        )


        styles = getSampleStyleSheet()

        elements = []


        # ---------------- TITLE ----------------
        title = Paragraph(

            "<b>BUYROUTE INVOICE</b>",

            styles['Title']
        )

        elements.append(title)

        elements.append(Spacer(1, 15))


        # ---------------- ORDER DETAILS ----------------
        order_info = f"""

        <b>Order ID:</b> {order_data[0]} <br/>

        <b>Razorpay Order ID:</b> {order_data[1]} <br/>

        <b>Payment ID:</b> {order_data[2]} <br/>

        <b>Order Date:</b> {order_data[7]} <br/>

        """


        order_para = Paragraph(

            order_info,

            styles['BodyText']
        )

        elements.append(order_para)

        elements.append(Spacer(1, 10))

        elements.append(HRFlowable(width="100%"))

        elements.append(Spacer(1, 15))


        # ---------------- TABLE DATA ----------------
        table_data = [[

            'Item Name',

            'Category',

            'Price',

            'Quantity',

            'Subtotal'
        ]]


        for item in order_items:

            table_data.append([

                item[0],

                item[4],

                f"₹{float(item[1])}",

                str(item[2]),

                f"₹{float(item[3])}"
            ])


        # ---------------- CREATE TABLE ----------------
        table = Table(

            table_data,

            colWidths=[180, 100, 80, 70, 80]
        )


        # ---------------- TABLE STYLE ----------------
        table.setStyle(

            TableStyle([

                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),

                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

                ('FONTSIZE', (0, 0), (-1, -1), 10),

                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),

                ('GRID', (0, 0), (-1, -1), 1, colors.black),

                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),

                ('ALIGN', (2, 1), (-1, -1), 'CENTER')
            ])
        )

        elements.append(table)

        elements.append(Spacer(1, 20))


        # ---------------- SUMMARY ----------------
        summary = f"""

        <b>Items Total:</b> ₹{float(order_data[3])}<br/><br/>

        <b>Delivery:</b> ₹{float(order_data[4])}<br/><br/>

        <b>Tax:</b> ₹{float(order_data[5])}<br/><br/>

        <b>Grand Total:</b> ₹{float(order_data[6])}

        """


        summary_para = Paragraph(

            summary,

            styles['Heading3']
        )

        elements.append(summary_para)

        elements.append(Spacer(1, 25))


        # ---------------- FOOTER ----------------
        footer = Paragraph(

            "Thank you for shopping with BUYROUTE",

            styles['Italic']
        )

        elements.append(footer)


        # ---------------- BUILD PDF ----------------
        doc.build(elements)

        pdf_buffer.seek(0)


        # ---------------- RESPONSE ----------------
        response = make_response(

            pdf_buffer.getvalue()
        )

        response.headers['Content-Type'] = 'application/pdf'

        response.headers['Content-Disposition'] = (

            f'attachment; filename=invoice_{ord_id}.pdf'
        )

        return response


    except Exception as e:

        print(f'Invoice Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/category/<ctype>',
    methods=['GET']
)
def category(ctype):

    cursor = None

    try:

        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        # ---------------- FETCH CATEGORY ITEMS ----------------
        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            FROM items

            WHERE category=%s
            ''',
            [ctype]
        )

        items_data = cursor.fetchall()


        # ---------------- EMPTY CATEGORY ----------------
        if not items_data:

            return jsonify({

                'status': 'failed',

                'message': 'No items found'

            }), 404


        # ---------------- FORMAT RESPONSE ----------------
        all_items = []


        for item in items_data:

            image_url = url_for(

                'static',

                filename=f'uploads/{item[7]}',

                _external=True
            )


            all_items.append({

                'itemid': item[0],

                'itemname': item[1],

                'description': item[2],

                'about': item[3],

                'price': float(item[4]),

                'quantity': int(item[5]),

                'category': item[6],

                'image': image_url
            })


        # ---------------- FINAL RESPONSE ----------------
        return jsonify({

            'status': 'success',

            'category': ctype,

            'total_items': len(all_items),

            'products': all_items
        })


    except Exception as e:

        print(f'Category Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)

        }), 500


    finally:

        if cursor:
            cursor.close()

@app.route(
    '/api/items/<itemid>',
    methods=['GET']
)
def descitem(itemid):

    cursor = None

    try:

        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT 
                BIN_TO_UUID(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            FROM items

            WHERE itemid = uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item_data = cursor.fetchone()


        if not item_data:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        image_url = url_for(

            'static',

            filename=f'uploads/{item_data[7]}',

            _external=True
        )


        item_details = {

            'itemid': item_data[0],

            'itemname': item_data[1],

            'description': item_data[2],

            'about': item_data[3],

            'price': float(item_data[4]),

            'quantity': int(item_data[5]),

            'category': item_data[6],

            'image_url': image_url
        }


        return jsonify({

            'status': 'success',

            'item': item_details

        }), 200


    except Exception as e:

        print(f'Item Details Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': 'Could not fetch item details'

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/add-review/<itemid>',
    methods=['POST']
)
def addreview(itemid):

    cursor = None

    try:

        # ---------------- LOGIN VALIDATION ----------------
        if 'userid' not in session:

            return jsonify({

                'status': 'failed',

                'message': 'Please login first'

            }), 401


        data = request.get_json()

        if not data:

            return jsonify({

                'status': 'failed',

                'message': 'No input data'

            }), 400


        rating = data.get('rating')

        review_text = data.get('review_text')


        # ---------------- VALIDATION ----------------
        if not rating or not review_text:

            return jsonify({

                'status': 'failed',

                'message': 'Rating and review are required'

            }), 400


        if int(rating) < 1 or int(rating) > 5:

            return jsonify({

                'status': 'failed',

                'message': 'Rating must be between 1 and 5'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        userid = session.get('userid')


        # ---------------- CHECK ITEM EXISTS ----------------
        cursor.execute(
            '''
            SELECT COUNT(*)

            FROM items

            WHERE itemid = uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item_exists = cursor.fetchone()[0]


        if item_exists == 0:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'

            }), 404


        # ---------------- INSERT REVIEW ----------------
        cursor.execute(
            '''
            INSERT INTO reviews
            (
                r_text,
                rating,
                itemid,
                userid
            )

            VALUES
            (
                %s,
                %s,
                uuid_to_bin(%s),
                uuid_to_bin(%s)
            )
            ''',
            [
                review_text,
                rating,
                itemid,
                userid
            ]
        )


        mydb.commit()


        return jsonify({

            'status': 'success',

            'message': 'Review added successfully'

        }), 201


    except Exception as e:

        mydb.rollback()

        print(f'Review Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': 'Could not add review'

        }), 500


    finally:

        if cursor:
            cursor.close()


@app.route(
    '/api/search',
    methods=['GET']
)
def usersearch():

    cursor = None

    try:

        # get search query from URL
        searchdata = request.args.get(
            'q',
            ''
        ).strip()


        # empty validation
        if not searchdata:

            return jsonify({

                'status': 'failed',

                'message': 'Search query required'

            }), 400


        # regex validation
        pattern = re.compile(
            r'^[A-Za-z0-9 ]+$',
            re.IGNORECASE
        )

        if not pattern.match(searchdata):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid search'

            }), 400


        # reconnect automatically if mysql connection lost
        mydb.ping(reconnect=True)

        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT

                BIN_TO_UUID(itemid),

                itemname,

                item_desc,

                item_about,

                price,

                quantity,

                category,

                item_img

            FROM items

            WHERE

                itemname LIKE %s

                OR item_desc LIKE %s

                OR category LIKE %s
            ''',

            [
                '%' + searchdata + '%',

                '%' + searchdata + '%',

                '%' + searchdata + '%'
            ]
        )


        allitem_data = cursor.fetchall()


        items = []


        for item in allitem_data:

            image_url = url_for(

                'static',

                filename=f'uploads/{item[7]}',

                _external=True
            )


            items.append({

                'itemid': item[0],

                'itemname': item[1],

                'description': item[2],

                'about': item[3],

                'price': float(item[4]),

                'quantity': item[5],

                'category': item[6],

                'image_url': image_url
            })


        return jsonify({

            'status': 'success',

            'total_items': len(items),

            'items': items

        }), 200


    except Exception as e:

        print(f'Search Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': 'Could not fetch item details'

        }), 500


    finally:

        if cursor:
            cursor.close()
if __name__=='__main__':

    app.run()
