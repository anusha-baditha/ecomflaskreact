from flask import Flask,request,jsonify,session,make_response
from flask_cors import CORS
from flask_session import Session
from flask_bcrypt import Bcrypt
from mysql.connector import connection
from cmail import send_mail 
from otp import genotp
import os
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

import re
import os
app=Flask(__name__)

# enable react connection
CORS(
    app,
    supports_credentials=True
)

bcrypt=Bcrypt(app)

# session config
app.secret_key='code123'

app.config['SESSION_TYPE']='filesystem'

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
    user='flaskuser',
    password='password',
    host='localhost',
    database='flaskdb'
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

    try:

        cursor=mydb.cursor(buffered=True)

        cursor.execute(
            '''
            select
            bin_to_uuid(itemid),
            itemname,
            item_desc,
            item_about,
            price,
            quantity,
            category,
            item_img
            from items
            '''
        )

        allitems_data=cursor.fetchall()

        products=[]


        for item in allitems_data:

            products.append({

                'itemid':item[0],

                'itemname':item[1],

                'item_desc':item[2],

                'item_about':item[3],

                'price':item[4],

                'quantity':item[5],

                'category':item[6],

                'image':
                f'http://127.0.0.1:5000/static/uploads/{item[7]}'
            })


        cursor.close()


        return jsonify({

            'status':'success',

            'products':products
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/register',
    methods=['POST']
)
def admincreate():

    try:

        # receive JSON data from React
        data=request.get_json()


        # extract values
        admin_name=data.get('username').strip()

        admin_email=data.get('useremail').strip()

        admin_address=data.get('useraddress').strip()

        admin_password=data.get('userpassword').strip()

        admin_agree=data.get('useragree')


        # database connection
        cursor=mydb.cursor(buffered=True)


        # check email exists
        cursor.execute(
            '''
            select count(*)
            from admindata
            where admin_email=%s
            ''',
            [admin_email]
        )

        email_count=cursor.fetchone()[0]


        # email already exists
        if email_count>0:

            return jsonify({

                'status':'failed',

                'message':'Email already exists'
            }),400


        # generate OTP
        gotp=genotp()


        # temporary admin data
        admindata={

            'admin_username':admin_name,

            'admin_useremail':admin_email,

            'admin_address':admin_address,

            'admin_userpassword':admin_password,

            'admin_agree':admin_agree,

            'admin_otp':gotp
        }


        # email details
        subject='Admin Registration Verification'

        body=f'Use OTP for verification: {gotp}'


        # send email
        send_mail(
            to=admin_email,
            subject=subject,
            body=body
        )


        # encrypt temporary data
        token=endata(admindata)


        # success response
        return jsonify({

            'status':'success',

            'message':'OTP sent successfully',

            'token':token
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/verify-otp',
    methods=['POST']
)
def adminotpverify():

    try:

        # receive JSON data
        data=request.get_json()


        # get frontend values
        userotp=data.get('otp')

        token=data.get('token')


        # decrypt token
        admin_details=dndata(token)


        # OTP validation
        if userotp!=admin_details['admin_otp']:

            return jsonify({

                'status':'failed',

                'message':'Invalid OTP'
            }),400


        # hash password
        hash_password=bcrypt.generate_password_hash(
            admin_details['admin_userpassword']
        ).decode('utf-8')


        # database insert
        cursor=mydb.cursor(buffered=True)

        cursor.execute(
            '''
            insert into admindata(
                adminid,
                adminname,
                admin_email,
                admin_password,
                admin_address,
                admin_agree
            )
            values(
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
                hash_password,
                admin_details['admin_address'],
                admin_details['admin_agree']
            ]
        )

        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Admin Registered Successfully'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/login',
    methods=['POST']
)
def adminlogin():

    try:

        # receive JSON data
        data=request.get_json()


        # extract values
        login_email=data.get('email')

        login_password=data.get('password')


        # database connection
        cursor=mydb.cursor(buffered=True)


        # check email exists
        cursor.execute(
            '''
            select count(*)
            from admindata
            where admin_email=%s
            ''',
            [login_email]
        )

        email_count=cursor.fetchone()[0]


        # email not found
        if email_count==0:

            return jsonify({

                'status':'failed',

                'message':'No Email Found'
            }),404


        # get hashed password
        cursor.execute(
            '''
            select admin_password
            from admindata
            where admin_email=%s
            ''',
            [login_email]
        )

        stored_password=cursor.fetchone()[0]


        # password verification
        if not bcrypt.check_password_hash(
            stored_password,
            login_password
        ):

            return jsonify({

                'status':'failed',

                'message':'Invalid Password'
            }),401


        # create session
        session['admin']=login_email


        # success response
        return jsonify({

            'status':'success',

            'message':'Login Successful',

            'admin':{

                'email':login_email
            }
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/dashboard',
    methods=['GET']
)
def admindashboard():

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # success response
        return jsonify({

            'status':'success',

            'message':'Welcome Admin',

            'admin':session.get('admin')
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
def allowed_file(filename:str)->bool:

    return (
        "." in filename and
        filename.rsplit('.',1)[1].lower()
        in ALLOWED_EXTENSIONS
    )
@app.route(
    '/api/admin/add-item',
    methods=['POST']
)
def additem():

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # receive form data
        item_name=request.form.get('title')

        item_description=request.form.get('Description')

        item_about=request.form.get('About_item')

        item_quantity=request.form.get('quantity')

        item_price=request.form.get('price')

        item_category=request.form.get('category')


        # receive image
        item_filedata=request.files.get('file')


        # image validation
        if not item_filedata:

            return jsonify({

                'status':'failed',

                'message':'Image file required'
            }),400


        filename=item_filedata.filename


        # extension validation
        if not allowed_file(filename):

            return jsonify({

                'status':'failed',

                'message':'Only png,jpg,jpeg,webp,gif allowed'
            }),400


        # secure filename
        orig_secure=secure_filename(filename)

        ext=os.path.splitext(orig_secure)[1]


        # generate unique filename
        filename=genotp()+ext


        # full save path
        save_path=os.path.join(

            app.config['UPLOAD_FOLDER'],

            filename
        )


        # save image
        item_filedata.save(save_path)


        # database
        cursor=mydb.cursor(buffered=True)


        # get admin id
        cursor.execute(
            '''
            select adminid
            from admindata
            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        adminid=cursor.fetchone()[0]


        # insert item
        cursor.execute(
            '''
            insert into items(

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

            values(

                uuid_to_bin(uuid()),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
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

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Item Added Successfully',

            'image':
            f'/static/uploads/{filename}'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/items',
    methods=['GET']
)
def viewallitems():

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # database cursor
        cursor=mydb.cursor()


        # get admin id
        cursor.execute(
            '''
            select adminid
            from admindata
            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        adminid=cursor.fetchone()


        # admin validation
        if not adminid:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        adminid=adminid[0]


        # fetch items
        cursor.execute(
            '''
            select

            bin_to_uuid(itemid),
            itemname,
            item_desc,
            item_about,
            price,
            quantity,
            category,
            item_img

            from items

            where added_by=%s
            ''',
            [adminid]
        )


        allitems_data=cursor.fetchall()


        # convert tuple → JSON
        products=[]


        for item in allitems_data:

            products.append({

                'itemid':item[0],

                'itemname':item[1],

                'item_desc':item[2],

                'item_about':item[3],

                'price':item[4],

                'quantity':item[5],

                'category':item[6],

                'image':
                f'http://127.0.0.1:5000/static/uploads/{item[7]}'
            })


        cursor.close()


        return jsonify({

            'status':'success',

            'products':products
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/item/<itemid>',
    methods=['GET']
)
def viewitem(itemid):

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # database cursor
        cursor=mydb.cursor()


        # get admin id
        cursor.execute(
            '''
            select adminid
            from admindata
            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        adminid=cursor.fetchone()


        # admin validation
        if not adminid:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        adminid=adminid[0]


        # fetch single item
        cursor.execute(
            '''
            select

            bin_to_uuid(itemid),
            itemname,
            item_desc,
            item_about,
            price,
            quantity,
            category,
            item_img

            from items

            where
            added_by=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [adminid,itemid]
        )


        item_data=cursor.fetchone()


        # item validation
        if not item_data:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        # tuple → JSON
        product={

            'itemid':item_data[0],

            'itemname':item_data[1],

            'item_desc':item_data[2],

            'item_about':item_data[3],

            'price':item_data[4],

            'quantity':item_data[5],

            'category':item_data[6],

            'image':
            f'http://127.0.0.1:5000/static/uploads/{item_data[7]}'
        }


        cursor.close()


        return jsonify({

            'status':'success',

            'product':product
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/delete-item/<itemid>',
    methods=['DELETE']
)
def deleteitem(itemid):

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # database cursor
        cursor=mydb.cursor()


        # get admin id
        cursor.execute(
            '''
            select adminid
            from admindata
            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        adminid=cursor.fetchone()


        # admin validation
        if not adminid:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        adminid=adminid[0]


        # fetch item
        cursor.execute(
            '''
            select

            item_img

            from items

            where
            itemid=uuid_to_bin(%s)
            and added_by=%s
            ''',
            [itemid,adminid]
        )

        item_data=cursor.fetchone()


        # item validation
        if not item_data:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        # image filename
        image_name=item_data[0]


        # full image path
        remove_path=os.path.join(

            app.config['UPLOAD_FOLDER'],

            image_name
        )


        # delete image file
        if os.path.exists(remove_path):

            os.remove(remove_path)


        # delete database record
        cursor.execute(
            '''
            delete from items

            where
            itemid=uuid_to_bin(%s)
            and added_by=%s
            ''',
            [itemid,adminid]
        )

        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Item Deleted Successfully'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/update-item/<itemid>',
    methods=['PUT']
)
def updateitem(itemid):

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # database cursor
        cursor=mydb.cursor()


        # get admin id
        cursor.execute(
            '''
            select adminid
            from admindata
            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        adminid=cursor.fetchone()


        # admin validation
        if not adminid:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        adminid=adminid[0]


        # fetch existing item
        cursor.execute(
            '''
            select

            item_img

            from items

            where
            added_by=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [adminid,itemid]
        )

        item_data=cursor.fetchone()


        # item validation
        if not item_data:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        old_image=item_data[0]


        # receive form data
        updateditem_name=request.form.get('title')

        updateditem_description=request.form.get('Description')

        updateditem_about=request.form.get('About_item')

        updateditem_quantity=request.form.get('quantity')

        updateditem_price=request.form.get('price')

        updateditem_category=request.form.get('category')


        # receive image
        updateditem_filedata=request.files.get('file')


        # default old image
        filename=old_image


        # if new image uploaded
        if updateditem_filedata:

            uploaded_filename=updateditem_filedata.filename


            # extension validation
            if not allowed_file(uploaded_filename):

                return jsonify({

                    'status':'failed',

                    'message':'Only png,jpg,jpeg,webp,gif allowed'
                }),400


            # secure filename
            orig_secure=secure_filename(uploaded_filename)

            ext=os.path.splitext(orig_secure)[1]


            # generate unique filename
            filename=genotp()+ext


            # full save path
            save_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                filename
            )


            # save new image
            updateditem_filedata.save(save_path)


            # delete old image
            old_image_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                old_image
            )


            if os.path.exists(old_image_path):

                os.remove(old_image_path)


        # update database
        cursor.execute(
            '''
            update items

            set

            itemname=%s,
            item_desc=%s,
            item_about=%s,
            price=%s,
            quantity=%s,
            category=%s,
            item_img=%s

            where
            added_by=%s
            and itemid=uuid_to_bin(%s)
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


        return jsonify({

            'status':'success',

            'message':'Item Updated Successfully',

            'image':
            f'/static/uploads/{filename}'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/profile-update',
    methods=['PUT']
)
def adminprofileupdate():

    try:

        # session validation
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # database cursor
        cursor=mydb.cursor()


        # fetch admin details
        cursor.execute(
            '''
            select

            adminid,
            adminname,
            admin_phoneno,
            admin_address,
            admin_imgdata

            from admindata

            where admin_email=%s
            ''',
            [session.get('admin')]
        )

        admin_data=cursor.fetchone()


        # admin validation
        if not admin_data:

            return jsonify({

                'status':'failed',

                'message':'Admin not found'
            }),404


        # existing image
        old_image=admin_data[4]


        # receive form data
        updated_adminname=request.form.get('adminname')

        updated_adminaddress=request.form.get('address')

        updated_adminphone=request.form.get('ph_no')


        # receive file
        updated_adminprofile=request.files.get('file')


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


            # secure filename
            orig_secure=secure_filename(uploaded_filename)

            ext=os.path.splitext(orig_secure)[1]


            # generate unique filename
            filename=genotp()+ext


            # save path
            save_path=os.path.join(

                app.config['UPLOAD_FOLDER'],

                filename
            )


            # save new image
            updated_adminprofile.save(save_path)


            # delete old image
            if old_image:

                old_image_path=os.path.join(

                    app.config['UPLOAD_FOLDER'],

                    old_image
                )


                if os.path.exists(old_image_path):

                    os.remove(old_image_path)


        # update database
        cursor.execute(
            '''
            update admindata

            set

            adminname=%s,
            admin_address=%s,
            admin_phoneno=%s,
            admin_imgdata=%s

            where adminid=%s
            ''',
            [

                updated_adminname,
                updated_adminaddress,
                updated_adminphone,
                filename,
                admin_data[0]
            ]
        )


        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Admin Profile Updated Successfully',

            'profile_image':
            f'/static/uploads/{filename}'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/admin/logout',
    methods=['POST']
)
def adminlogout():

    try:

        # check session
        if not session.get('admin'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # remove admin session
        session.pop('admin')


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

    try:

        # receive frontend data
        data=request.get_json()


        # form values
        user_name=data.get('name','').strip()

        user_email=data.get('email','').strip()

        user_address=data.get('address','').strip()

        user_password=data.get('password','').strip()

        user_phone=data.get('phone_no','').strip()

        user_gender=data.get('usergender','').strip()


        # validations
        if not user_name:

            return jsonify({

                'status':'failed',

                'message':'Name required'
            }),400


        if not user_email:

            return jsonify({

                'status':'failed',

                'message':'Email required'
            }),400


        if not user_password:

            return jsonify({

                'status':'failed',

                'message':'Password required'
            }),400


        # database cursor
        cursor=mydb.cursor()


        # check email exists
        cursor.execute(
            '''
            select count(*)

            from userdata

            where useremail=%s
            ''',
            [user_email]
        )

        email_count=cursor.fetchone()[0]


        # email already exists
        if email_count==1:

            return jsonify({

                'status':'failed',

                'message':'Email already exists'
            }),409


        # generate otp
        gotp=genotp()


        # temporary userdata
        userdata={

            'user_username':user_name,

            'user_useremail':user_email,

            'user_address':user_address,

            'user_userpassword':user_password,

            'user_phone':user_phone,

            'user_gender':user_gender,

            'user_otp':gotp
        }


        # encrypt userdata
        encrypted_data=endata(userdata)


        # send email
        subject='User Registration Verification'

        body=f'Use this OTP for verification: {gotp}'


        send_mail(

            to=user_email,

            subject=subject,

            body=body
        )


        cursor.close()


        return jsonify({

            'status':'success',

            'message':'OTP sent successfully',

            'verification_token':encrypted_data
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route(
    '/api/user/verify-otp',
    methods=['POST']
)
def userotpverify():

    try:

        # receive frontend data
        data=request.get_json()


        # frontend values
        userdata=data.get('verification_token')

        userotp=data.get('otp')


        # decrypt userdata
        try:

            user_details=dndata(userdata)

        except Exception:

            return jsonify({

                'status':'failed',

                'message':'Invalid verification token'
            }),400


        # otp validation
        if userotp != user_details['user_otp']:

            return jsonify({

                'status':'failed',

                'message':'Invalid OTP'
            }),400


        # password hashing
        hash_password=bcrypt.generate_password_hash(

            user_details['user_userpassword']

        ).decode('utf-8')


        # database cursor
        cursor=mydb.cursor()


        # insert user
        cursor.execute(
            '''
            insert into userdata(

                userid,
                username,
                useremail,
                password,
                useraddress,
                usergender,
                userphone

            )

            values(

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

                hash_password,

                user_details['user_address'],

                user_details['user_gender'],

                user_details['user_phone']
            ]
        )


        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'User registered successfully'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500

@app.route(
    '/api/user/login',
    methods=['POST']
)
def userlogin():

    try:

        # receive frontend data
        data=request.get_json()


        login_email=data.get('email')

        login_password=data.get('password')


        # validations
        if not login_email:

            return jsonify({

                'status':'failed',

                'message':'Email required'
            }),400


        if not login_password:

            return jsonify({

                'status':'failed',

                'message':'Password required'
            }),400


        # database cursor
        cursor=mydb.cursor()


        # check email exists
        cursor.execute(
            '''
            select password

            from userdata

            where useremail=%s
            ''',
            [login_email]
        )

        user_data=cursor.fetchone()


        # email validation
        if not user_data:

            return jsonify({

                'status':'failed',

                'message':'No Email Found'
            }),404


        stored_password=user_data[0]


        # password validation
        if not bcrypt.check_password_hash(

            stored_password,

            login_password
        ):

            return jsonify({

                'status':'failed',

                'message':'Invalid Password'
            }),401


        # create session
        session['user']=login_email


        # optional cart session
        if not session.get(login_email):

            session[login_email]={}


        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Login Successful',

            'user':login_email
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/user/logout',
    methods=['POST']
)
def userlogout():

    try:

        # check session
        if not session.get('user'):

            return jsonify({

                'status':'failed',

                'message':'Please login first'
            }),401


        # remove session
        session.pop('user')


        return jsonify({

            'status':'success',

            'message':'Logout successful'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500
@app.route(
    '/api/cart/add',
    methods=['POST']
)
def addcart():

    # login check
    if not session.get('user'):

        return jsonify({

            'status':'failed',

            'message':'Please login first'
        }),401


    try:

        # frontend data
        data=request.get_json()

        itemid=data.get('itemid')

        quantity=data.get('quantity',1)


        cursor=mydb.cursor()


        # get userid
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # check item exists
        cursor.execute(
            '''
            select quantity

            from items

            where itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item=cursor.fetchone()


        if not item:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        # stock validation
        if quantity > item[0]:

            return jsonify({

                'status':'failed',

                'message':'Insufficient stock'
            }),400


        # already in cart?
        cursor.execute(
            '''
            select quantity

            from cart

            where userid=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [userid,itemid]
        )

        existing_cart=cursor.fetchone()


        # update quantity
        if existing_cart:

            new_quantity=existing_cart[0] + quantity

            cursor.execute(
                '''
                update cart

                set quantity=%s

                where userid=%s
                and itemid=uuid_to_bin(%s)
                ''',
                [new_quantity,userid,itemid]
            )

            message='Cart quantity updated'


        # insert new item
        else:

            cursor.execute(
                '''
                insert into cart(

                    cartid,
                    userid,
                    itemid,
                    quantity

                )

                values(

                    uuid_to_bin(uuid()),
                    %s,
                    uuid_to_bin(%s),
                    %s
                )
                ''',
                [userid,itemid,quantity]
            )

            message='Item added to cart'


        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':message
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route(
    '/api/cart/view',
    methods=['GET']
)
def viewcart():

    # login check
    if not session.get('user'):

        return jsonify({

            'status':'failed',

            'message':'Please login first'
        }),401


    try:

        cursor=mydb.cursor()


        # get user id
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # fetch cart items
        cursor.execute(
            '''
            select

                bin_to_uuid(i.itemid),

                i.itemname,

                i.price,

                c.quantity,

                i.category,

                i.item_img

            from cart c

            join items i

            on c.itemid=i.itemid

            where c.userid=%s
            ''',
            [userid]
        )

        cart_items=cursor.fetchall()


        # empty cart
        if not cart_items:

            return jsonify({

                'status':'failed',

                'message':'Cart is empty'
            }),404


        subtotal=0

        items_data=[]


        for item in cart_items:

            itemid=item[0]

            item_name=item[1]

            item_price=float(item[2])

            item_quantity=int(item[3])

            item_category=item[4]

            item_imgname=item[5]


            total=item_price * item_quantity

            subtotal += total


            items_data.append({

                'itemid':itemid,

                'itemname':item_name,

                'price':item_price,

                'quantity':item_quantity,

                'category':item_category,

                'image':item_imgname,

                'total':total
            })


        delivery=40

        tax=round(subtotal * 0.05,2)

        grand_total=subtotal + delivery + tax


        cursor.close()


        return jsonify({

            'status':'success',

            'cart_items':items_data,

            'summary':{

                'subtotal':subtotal,

                'delivery':delivery,

                'tax':tax,

                'grand_total':grand_total
            }
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route(
    '/api/cart/update',
    methods=['PUT']
)
def updatecart():

    # login check
    if not session.get('user'):

        return jsonify({

            'status':'failed',

            'message':'Please login first'
        }),401


    try:

        # frontend data
        data=request.get_json()


        itemid=data.get('itemid')

        updated_quantity=int(
            data.get('quantity')
        )


        # quantity validation
        if updated_quantity <= 0:

            return jsonify({

                'status':'failed',

                'message':'Quantity must be greater than 0'
            }),400


        cursor=mydb.cursor()


        # get userid
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # check cart item exists
        cursor.execute(
            '''
            select quantity

            from cart

            where userid=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [userid,itemid]
        )

        cart_item=cursor.fetchone()


        if not cart_item:

            return jsonify({

                'status':'failed',

                'message':'Item not in cart'
            }),404


        # stock validation
        cursor.execute(
            '''
            select quantity

            from items

            where itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        stock_item=cursor.fetchone()


        if not stock_item:

            return jsonify({

                'status':'failed',

                'message':'Item not found'
            }),404


        available_stock=stock_item[0]


        if updated_quantity > available_stock:

            return jsonify({

                'status':'failed',

                'message':'Insufficient stock'
            }),400


        # update quantity
        cursor.execute(
            '''
            update cart

            set quantity=%s

            where userid=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [updated_quantity,userid,itemid]
        )


        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Cart updated successfully'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route(
    '/api/cart/remove/<itemid>',
    methods=['DELETE']
)
def removecart(itemid):

    # login check
    if not session.get('user'):

        return jsonify({

            'status':'failed',

            'message':'Please login first'
        }),401


    try:

        cursor=mydb.cursor()


        # get userid
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # check item exists in cart
        cursor.execute(
            '''
            select quantity

            from cart

            where userid=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [userid,itemid]
        )

        cart_item=cursor.fetchone()


        if not cart_item:

            return jsonify({

                'status':'failed',

                'message':'Item not in cart'
            }),404


        # remove cart item
        cursor.execute(
            '''
            delete from cart

            where userid=%s
            and itemid=uuid_to_bin(%s)
            ''',
            [userid,itemid]
        )


        mydb.commit()

        cursor.close()


        return jsonify({

            'status':'success',

            'message':'Item removed from cart'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500



@app.route(
    '/api/payment/create-order',
    methods=['POST']
)
def pay_cart():

    # login validation
    if not session.get('user'):

        return jsonify({

            'status':'failed',

            'message':'Please login first'
        }),401


    try:

        data=request.get_json()

        payment_type=data.get('type','cart')

        cursor=mydb.cursor(buffered=True)


        # get user id
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # CART PAYMENT
        if payment_type == 'cart':

            cursor.execute(
                '''
                select

                    bin_to_uuid(i.itemid),

                    i.itemname,

                    i.price,

                    c.quantity,

                    i.category,

                    i.item_img

                from cart c

                join items i

                on c.itemid=i.itemid

                where c.userid=%s
                ''',
                [userid]
            )

            cart_items=cursor.fetchall()


        # SINGLE BUY
        else:

            itemid=data.get('itemid')

            quantity=int(data.get('quantity',1))


            cursor.execute(
                '''
                select

                    bin_to_uuid(itemid),

                    itemname,

                    price,

                    category,

                    item_img

                from items

                where itemid=uuid_to_bin(%s)
                ''',
                [itemid]
            )

            item=cursor.fetchone()


            if not item:

                return jsonify({

                    'status':'failed',

                    'message':'Item not found'
                }),404


            cart_items=[(

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

                'status':'failed',

                'message':'Cart is empty'
            }),404


        subtotal=0

        items_data=[]


        for item in cart_items:

            itemid=item[0]

            item_name=item[1]

            item_price=float(item[2])

            item_quantity=int(item[3])

            item_category=item[4]

            item_img=item[5]


            amount=item_price * item_quantity

            subtotal += amount


            items_data.append({

                'itemid':itemid,

                'itemname':item_name,

                'price':item_price,

                'quantity':item_quantity,

                'category':item_category,

                'image':item_img,

                'amount':amount
            })


        delivery=40

        tax=round(subtotal * 0.05,2)

        grand_total=subtotal + delivery + tax


        razorpay_amount=int(
            grand_total * 100
        )


        # create razorpay order
        order=client.order.create({

            "amount":razorpay_amount,

            "currency":"INR",

            "receipt":session.get('user'),

            "payment_capture":1
        })


        return jsonify({

            'status':'success',

            'order':{

                'order_id':order['id'],

                'amount':order['amount'],

                'currency':order['currency']
            },

            'cart_items':items_data,

            'summary':{

                'subtotal':subtotal,

                'delivery':delivery,

                'tax':tax,

                'grand_total':grand_total
            },

            'razorpay_key':'rzp_test_SHy3zlzWZXNg3W'
        })


    except Exception as e:

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route(
    '/api/payment/verify',
    methods=['POST']
)
def verify_payment():

    try:

        data=request.get_json()


        # -----------------------------------
        # GET FRONTEND DATA
        # -----------------------------------

        payment_id=data.get(
            'razorpay_payment_id'
        )

        order_id=data.get(
            'razorpay_order_id'
        )

        signature=data.get(
            'razorpay_signature'
        )

        mode=data.get(
            'mode',
            'cart'
        )


        # -----------------------------------
        # VERIFY SIGNATURE
        # -----------------------------------

        params_dict={

            'razorpay_order_id':order_id,

            'razorpay_payment_id':payment_id,

            'razorpay_signature':signature
        }


        try:

            client.utility.verify_payment_signature(
                params_dict
            )

        except Exception as e:

            print(e)

            return jsonify({

                'status':'failed',

                'message':'Payment verification failed'
            }),400


        cursor=mydb.cursor(buffered=True)


        # -----------------------------------
        # TEMP USER
        # -----------------------------------

        # Later React login session
        # will replace this

        user_email=session.get('user')

        if not user_email:

            user_email='testuser@gmail.com'


        # -----------------------------------
        # GET USER
        # -----------------------------------

        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [user_email]
        )

        user=cursor.fetchone()


        if not user:

            return jsonify({

                'status':'failed',

                'message':'User not found'
            }),404


        userid=user[0]


        # -----------------------------------
        # GET CART ITEMS
        # -----------------------------------

        if mode=='cart':

            cursor.execute(
                '''
                select

                    bin_to_uuid(i.itemid),

                    i.itemname,

                    i.price,

                    c.quantity,

                    i.category,

                    i.item_img

                from cart c

                join items i

                on c.itemid=i.itemid

                where c.userid=%s
                ''',
                [userid]
            )

            cart_items=cursor.fetchall()


        # -----------------------------------
        # SINGLE BUY
        # -----------------------------------

        else:

            itemid=data.get('itemid')

            quantity=int(
                data.get('quantity',1)
            )


            cursor.execute(
                '''
                select

                    bin_to_uuid(itemid),

                    itemname,

                    price,

                    category,

                    item_img

                from items

                where itemid=uuid_to_bin(%s)
                ''',
                [itemid]
            )

            item=cursor.fetchone()


            if not item:

                return jsonify({

                    'status':'failed',

                    'message':'Item not found'
                }),404


            cart_items=[(

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

                'status':'failed',

                'message':'Cart empty'
            }),404


        # -----------------------------------
        # CALCULATE TOTAL
        # -----------------------------------

        subtotal=0


        for item in cart_items:

            item_price=float(item[2])

            item_quantity=int(item[3])

            subtotal += (
                item_price * item_quantity
            )


        delivery=40

        tax=round(subtotal * 0.05,2)

        grand_total=subtotal + delivery + tax


        # -----------------------------------
        # STORE ORDER
        # -----------------------------------

        cursor.execute(
            '''
            insert into orders(

                razorpay_ordid,

                razorpay_payment,

                userid,

                total_amount,

                delivery,

                tax,

                grand_total

            )

            values(

                %s,%s,%s,%s,%s,%s,%s
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


        order_table_id=cursor.lastrowid


        # -----------------------------------
        # STORE ORDER ITEMS
        # -----------------------------------

        insert_item_query='''
        insert into order_items(

            orderid,

            itemid,

            item_name,

            item_price,

            item_quantity,

            subtotal,

            item_category,

            item_filename

        )

        values(

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


        ordered_items=[]


        for item in cart_items:

            itemid=item[0]

            item_name=item[1]

            item_price=float(item[2])

            item_quantity=int(item[3])

            item_category=item[4]

            item_img=item[5]


            amount=item_price * item_quantity


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


            ordered_items.append({

                'itemid':itemid,

                'itemname':item_name,

                'price':item_price,

                'quantity':item_quantity,

                'subtotal':amount
            })


        # -----------------------------------
        # CLEAR CART
        # -----------------------------------

        if mode=='cart':

            cursor.execute(

                '''
                delete from cart

                where userid=%s
                ''',

                [userid]
            )


        mydb.commit()

        cursor.close()


        # -----------------------------------
        # SUCCESS RESPONSE
        # -----------------------------------

        return jsonify({

            'status':'success',

            'message':'Payment verified successfully',

            'payment':{

                'payment_id':payment_id,

                'order_id':order_id
            },

            'summary':{

                'subtotal':subtotal,

                'delivery':delivery,

                'tax':tax,

                'grand_total':grand_total
            },

            'ordered_items':ordered_items
        })


    except Exception as e:

        print(e)

        return jsonify({

            'status':'failed',

            'message':str(e)
        }),500


@app.route('/api/myorders',methods=['GET'])
def myorders():

    # check login
    if not session.get('user'):

        return jsonify({

            "status":"failed",

            "message":"Please login first"
        }),401

    try:

        cursor=mydb.cursor(buffered=True)

        # get logged user id
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user=cursor.fetchone()

        if not user:

            return jsonify({

                "status":"failed",

                "message":"User not found"
            }),404

        userid=user[0]

        # fetch all orders
        cursor.execute(
            '''
            select

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            from orders

            where userid=%s

            order by created_at desc
            ''',
            [userid]
        )

        orders=cursor.fetchall()

        cursor.close()

        all_orders=[]

        for order in orders:

            all_orders.append({

                "orderid":order[0],

                "razorpay_order_id":order[1],

                "razorpay_payment_id":order[2],

                "subtotal":float(order[3]),

                "delivery":float(order[4]),

                "tax":float(order[5]),

                "grand_total":float(order[6]),

                "created_at":str(order[7])
            })

        return jsonify({

            "status":"success",

            "orders":all_orders
        })

    except Exception as e:

        app.logger.exception(e)

        return jsonify({

            "status":"failed",

            "message":"Could not fetch orders"
        }),500


@app.route('/api/orders/<ordid>', methods=['GET'])
def myorder_details(ordid):

    # ---------------- LOGIN CHECK ----------------
    if not session.get('user'):

        return jsonify({

            'status': 'failed',

            'message': 'Please login first'
        }), 401

    try:

        cursor = mydb.cursor(buffered=True)

        # ---------------- GET USER ID ----------------
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user = cursor.fetchone()

        if not user:

            return jsonify({

                'status': 'failed',

                'message': 'User not found'
            }), 404

        userid = user[0]

        # ---------------- GET ORDER DETAILS ----------------
        cursor.execute(
            '''
            select

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            from orders

            where userid=%s and orderid=%s
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
            select

                order_detailsid,
                orderid,
                bin_to_uuid(itemid),
                item_name,
                item_price,
                item_quantity,
                subtotal,
                item_category,
                item_filename

            from order_items

            where orderid=%s
            ''',
            [ordid]
        )

        orders_itemsdata = cursor.fetchall()

        cursor.close()

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

            items_json.append({

                'order_details_id': item[0],

                'order_id': item[1],

                'itemid': item[2],

                'item_name': item[3],

                'item_price': float(item[4]),

                'item_quantity': int(item[5]),

                'subtotal': float(item[6]),

                'item_category': item[7],

                'item_image': item[8]
            })

        # ---------------- FINAL RESPONSE ----------------
        return jsonify({

            'status': 'success',

            'order': order_json,

            'items': items_json
        })

    except Exception as e:

        app.logger.exception(f'Order Details Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)
        }), 500


@app.route(
    '/api/buy-now',
    methods=['POST']
)
def buy_now():

    # ---------------- LOGIN CHECK ----------------
    if not session.get('user'):

        return jsonify({

            'status': 'failed',

            'message': 'Please login first'
        }), 401

    try:

        data = request.get_json()

        itemid = data.get('itemid')

        quantity = int(data.get('quantity', 1))

        if not itemid:

            return jsonify({

                'status': 'failed',

                'message': 'Item ID required'
            }), 400

        cursor = mydb.cursor(buffered=True)

        # ---------------- FETCH ITEM ----------------
        cursor.execute(
            '''
            select

                bin_to_uuid(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            from items

            where itemid=uuid_to_bin(%s)
            ''',
            [itemid]
        )

        item_data = cursor.fetchone()

        cursor.close()

        # ---------------- ITEM CHECK ----------------
        if not item_data:

            return jsonify({

                'status': 'failed',

                'message': 'Item not found'
            }), 404

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

                'image': item_data[7]
            },

            # frontend will use this
            'next_url': '/api/payment/create-order'
        })

    except Exception as e:

        app.logger.exception(f'Buy Now Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)
        }), 500



@app.route(
    '/api/invoice/<int:ord_id>',
    methods=['GET']
)
def get_invoice(ord_id):

    # ---------------- LOGIN CHECK ----------------
    if not session.get('user'):

        return jsonify({

            'status': 'failed',

            'message': 'Please login first'
        }), 401

    try:

        cursor = mydb.cursor(buffered=True)

        # ---------------- GET USER ----------------
        cursor.execute(
            '''
            select userid

            from userdata

            where useremail=%s
            ''',
            [session.get('user')]
        )

        user = cursor.fetchone()

        if not user:

            return jsonify({

                'status': 'failed',

                'message': 'User not found'
            }), 404

        userid = user[0]

        # ---------------- GET ORDER ----------------
        cursor.execute(
            '''
            select

                orderid,
                razorpay_ordid,
                razorpay_payment,
                total_amount,
                delivery,
                tax,
                grand_total,
                created_at

            from orders

            where userid=%s and orderid=%s
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
            select

                item_name,
                item_price,
                item_quantity,
                subtotal,
                item_category

            from order_items

            where orderid=%s
            ''',
            [ord_id]
        )

        order_items = cursor.fetchall()

        cursor.close()

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

        app.logger.exception(f'Invoice Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)
        }), 500


@app.route(
    '/api/category/<ctype>',
    methods=['GET']
)
def category(ctype):

    try:

        cursor = mydb.cursor(buffered=True)

        # ---------------- FETCH CATEGORY ITEMS ----------------
        cursor.execute(
            '''
            select

                bin_to_uuid(itemid),
                itemname,
                item_desc,
                item_about,
                price,
                quantity,
                category,
                item_img

            from items

            where category=%s
            ''',
            [ctype]
        )

        items_data = cursor.fetchall()

        cursor.close()

        # ---------------- EMPTY CATEGORY ----------------
        if not items_data:

            return jsonify({

                'status': 'failed',

                'message': 'No items found'
            }), 404

        # ---------------- FORMAT RESPONSE ----------------
        all_items = []

        for item in items_data:

            all_items.append({

                'itemid': item[0],

                'itemname': item[1],

                'description': item[2],

                'about': item[3],

                'price': float(item[4]),

                'quantity': int(item[5]),

                'category': item[6],

                'image': item[7]
            })

        # ---------------- FINAL RESPONSE ----------------
        return jsonify({

            'status': 'success',

            'category': ctype,

            'total_items': len(all_items),

            'products': all_items
        })

    except Exception as e:

        app.logger.exception(f'Category Error: {e}')

        return jsonify({

            'status': 'failed',

            'message': str(e)
        }), 500


@app.route('/api/items/<itemid>', methods=['GET'])
def descitem(itemid):

    try:

        cursor = mydb.cursor(buffered=True)

        cursor.execute(
            '''
            SELECT 
                bin_to_uuid(itemid),
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

        cursor.close()

        if not item_data:

            return jsonify({

                'status': 'failed',
                'message': 'Item not found'

            }), 404


        item_details = {

            'itemid': item_data[0],
            'itemname': item_data[1],
            'description': item_data[2],
            'about': item_data[3],
            'price': float(item_data[4]),
            'quantity': item_data[5],
            'category': item_data[6],

            'image_url': request.host_url + 
                         os.path.join(
                             'static/uploads',
                             item_data[7]
                         ).replace("\\","/")
        }


        return jsonify({

            'status': 'success',

            'item': item_details

        }), 200


    except Exception as e:

        print(e)

        return jsonify({

            'status': 'failed',

            'message': 'Could not fetch item details'

        }), 500


@app.route('/api/add-review/<itemid>', methods=['POST'])
def addreview(itemid):

    # login validation
    if not session.get('user'):

        return jsonify({

            'status': 'failed',

            'message': 'Please login first'

        }), 401


    try:

        data = request.get_json()

        rating = data.get('rating')

        review_text = data.get('review_text')


        # validation
        if not rating or not review_text:

            return jsonify({

                'status': 'failed',

                'message': 'Rating and review are required'

            }), 400


        cursor = mydb.cursor(buffered=True)


        # get user id
        cursor.execute(
            '''
            SELECT userid
            FROM userdata
            WHERE useremail=%s
            ''',
            [session.get('user')]
        )

        user = cursor.fetchone()


        if not user:

            return jsonify({

                'status': 'failed',

                'message': 'User not found'

            }), 404


        userid = user[0]


        # check item exists
        cursor.execute(
            '''
            SELECT count(*)
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


        # insert review
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
                %s
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

        cursor.close()


        return jsonify({

            'status': 'success',

            'message': 'Review added successfully'

        }), 201


    except Exception as e:

        print(e)

        return jsonify({

            'status': 'failed',

            'message': 'Could not add review'

        }), 500


@app.route('/api/search', methods=['GET'])
def usersearch():

    try:

        # get search query from URL
        searchdata = request.args.get('q', '').strip()


        # empty validation
        if not searchdata:

            return jsonify({

                'status': 'failed',

                'message': 'Search query required'

            }), 400


        # regex validation
        pattern = re.compile(r'^[A-Za-z0-9 ]+$', re.IGNORECASE)

        if not pattern.match(searchdata):

            return jsonify({

                'status': 'failed',

                'message': 'Invalid search'

            }), 400


        cursor = mydb.cursor(buffered=True)


        cursor.execute(
            '''
            SELECT

                bin_to_uuid(itemid),

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

                OR price LIKE %s

                OR category LIKE %s
            ''',

            [
                searchdata + '%',
                searchdata + '%',
                searchdata + '%',
                searchdata + '%'
            ]
        )


        allitem_data = cursor.fetchall()

        cursor.close()


        items = []


        for item in allitem_data:

            items.append({

                'itemid': item[0],

                'itemname': item[1],

                'description': item[2],

                'about': item[3],

                'price': float(item[4]),

                'quantity': item[5],

                'category': item[6],

                'image_url': request.host_url +

                             os.path.join(
                                 'static/uploads',
                                 item[7]
                             ).replace("\\","/")
            })


        return jsonify({

            'status': 'success',

            'total_items': len(items),

            'items': items

        }), 200


    except Exception as e:

        print(e)

        return jsonify({

            'status': 'failed',

            'message': 'Could not fetch item details'

        }), 500
if __name__=='__main__':

    app.run()
