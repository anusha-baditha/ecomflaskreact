from flask import Flask,redirect,url_for,render_template,request,flash,session,make_response
from xhtml2pdf import pisa
from io import BytesIO
from flask_session import Session
from otp import genotp
from werkzeug.utils import secure_filename
from cmail import send_mail
from stoken import endata,dndata
from flask_bcrypt import Bcrypt
from mysql.connector import (connection)
import os
import re
import razorpay
client = razorpay.Client(auth=("rzp_test_SHy3zlzWZXNg3W", "B67PBLrrvi1BP38vgyIEdOHg"))
BASE_DIR=os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER=os.path.join(BASE_DIR,'static','uploads')
ALLOWED_EXTENSIONS={"png",'jpg','gif','webp','jpeg'}
MAX_CONTENT_LENGTH=6 *1024*1024 #6MB
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
mydb=connection.MySQLConnection(user='root', password='admin',
                                 host='localhost',
                                 database='ecom22db')
app=Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key='code123'
app.config['SESSION_TYPE']='filesystem'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']=MAX_CONTENT_LENGTH
Session(app)
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items')
        allitems_data=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch all items')
        return redirect(url_for('index'))
    else:
        return render_template('index.html',allitems_data=allitems_data)
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        admin_name=request.form['username'].strip()
        admin_email=request.form['email'].strip()
        admin_address=request.form['address'].strip()
        admin_password=request.form['password'].strip()
        admin_agree=request.form['agree']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_email=%s ',[admin_email])
            email_count=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Could not verify user')
            return redirect(url_for('admincreate'))
        else:
            if email_count[0]==0:
                gotp=genotp()
                admindata={'admin_username':admin_name,'admin_useremail':admin_email,'admin_address':admin_address,'admin_userpassword':admin_password,'admin_agree':admin_agree,'admin_otp':gotp}
                subject=f'Admin registration verification'
                body=f'use the otp for verification {gotp}'
                send_mail(to=admin_email,subject=subject,body=body)
                flash('OTP has been sent to given mail')
                return redirect(url_for('adminotpverify',admindata=endata(admindata)))
            elif email_count[0]==1:
                flash('email already existed')
                return redirect(url_for('admincreate'))
            else:
                flash('Email not verified')
    return render_template('admincreate.html')
@app.route('/adminotpverify/<admindata>',methods=['GET','POST'])
def adminotpverify(admindata):
    try:
        admin_details=dndata(admindata)
    except Exception as e:
        flash('could not verify otp')
        return redirect(url_for('adminotpverify',admindata=admindata))
    else:
        if request.method=='POST':
            userotp=request.form['otp']
            if userotp==admin_details['admin_otp']:
                hash_password=bcrypt.generate_password_hash(admin_details['admin_userpassword'])
                print(hash_password)
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('insert into admindata(adminid,adminname,admin_email,admin_password,admin_address,admin_agree) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s)',[admin_details['admin_username'],admin_details['admin_useremail'],hash_password,admin_details['admin_address'],admin_details['admin_agree']])
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash('Colud not store admin details')
                    return redirect(url_for('adminotpverify',admindata=admindata))
                else:
                    flash('admin details successfully stored')
                    return redirect(url_for('adminlogin'))
            else:
                flash('Invalid otp')
                return redirect(url_for('adminotpverify',admindata=admindata))
        return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if request.method=='POST':
        login_email=request.form['email']
        login_password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_email=%s ',[login_email])
            email_count=cursor.fetchone()
            if email_count[0]==1:
                cursor.execute('select admin_password from admindata where admin_email=%s',[login_email])
                stored_password=cursor.fetchone()[0]
                if bcrypt.check_password_hash(stored_password,login_password):
                    session['admin']=login_email
                    return redirect(url_for('admindashboard'))
                else:
                    flash('invalid password')
                    return redirect(url_for('adminlogin'))
            elif email_count[0]==0:
                flash('No Email found')
                return redirect(url_for('adminlogin'))
        except Exception as e:
            print(e)
            flash('Could not verify user')
            return redirect(url_for('adminlogin'))
    return render_template('adminlogin.html')
@app.route('/admindashbard')
def admindashboard():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        flash('pls login to view dashboard')
        return redirect(url_for('adminlogin'))
def allowed_file(filename:str)->bool:
    return "." in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/additem',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            item_name=request.form['title']
            item_description=request.form['Description']
            item_about=request.form['About_item']
            item_quantity=request.form['quantity']
            item_price=request.form['price']
            item_category=request.form['category']
            item_filedata=request.files['file']
            print(item_filedata)
            print(item_filedata.filename)
            filename=item_filedata.filename
            if item_filedata and filename:
                if not allowed_file(filename):
                    flash('File type is not Allowed.pls give png,jpg,jpng,webp,gif')
                    return redirect(url_for('additem'))
                orig_secure=secure_filename(filename)
                ext=os.path.splitext(orig_secure)[1] #anusha.txt
                filename=genotp()+ext
                save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                try:
                    item_filedata.save(save_path)
                except Exception  as e:
                    flash('colud not store file data')
                    return redirect(url_for('additem'))
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
                    adminid=cursor.fetchone()[0]
                    if adminid:
                        cursor.execute('insert into items(itemid,itemname,item_desc,item_about,price,quantity,category,added_by,item_img) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s,%s)',[item_name,item_description,item_about,item_price,item_quantity,item_category,adminid,filename])
                        mydb.commit()
                        cursor.close()
                    else:
                        flash('user not found')
                        return redirect(url_for('additem'))
                except Exception as e:
                    print(e)
                    flash('could not add item')
                    return redirect(url_for('additem'))
                else:
                    flash('item added successfully')
                    return redirect(url_for('additem'))
        return render_template('additem.html') 
    else:
        flash('pls login to additem')
        return redirect(url_for('adminlogin'))
@app.route('/viewallitems')
def viewallitems():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
            if adminid:
                cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where added_by=%s ',[adminid])
                allitems_data=cursor.fetchall()
                print(allitems_data)
                cursor.close()
            else:
                flash('user not found')
                return redirect(url_for('additem'))
        except Exception as e:
            print(e)
            flash('could not fetch all items')
            return redirect(url_for('admindashboard'))
        else:
            return render_template('viewall_items.html',allitems_data=allitems_data)
    else:
        flash('pls login viewallitems')
        return redirect(url_for('adminlogin'))
@app.route('/viewitem/<itemid>')
def viewitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
            if adminid:
                cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where added_by=%s and itemid=uuid_to_bin(%s) ',[adminid,itemid])
                item_data=cursor.fetchone()
                cursor.close()
            else:
                flash('user not found')
                return redirect(url_for('additem'))
        except Exception as e:
            print(e)
            flash('could not fetch all items')
            return redirect(url_for('admindashboard'))
        else:
            return render_template('view_item.html',item_data=item_data)
    else:
        flash('pls login viewallitems')
        return redirect(url_for('adminlogin'))
@app.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
            if adminid:
                cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where added_by=%s and itemid=uuid_to_bin(%s) ',[adminid,itemid])
                item_data=cursor.fetchone()
                cursor.close()
            else:
                flash('user not found')
                return redirect(url_for('additem'))
        except Exception as e:
            print(e)
            flash('could not fetch all items')
            return redirect(url_for('admindashboard'))
        else:
            remove_path=os.path.join(app.config['UPLOAD_FOLDER'],item_data[7])
            try:
                if remove_path:
                    os.remove(remove_path)
                else:
                    flash('file not found')
                    return redirect(url_for('viewallitems'))
            except Exception as e:
                print(e)
                flash('Could not delete file')
                return redirect(url_for('viewallitems'))
            #delete from database
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
                adminid=cursor.fetchone()[0]
                cursor.execute('delete from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,adminid])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Could not delete item details')
                return redirect(url_for('viewallitems'))
            else:
                flash('item deleted succesfully')
                return redirect(url_for('viewallitems'))
    else:
        flash('pls login viewallitems')
        return redirect(url_for('adminlogin'))
@app.route('/updateitem/<itemid>',methods=['GET','POST'])
def updateitem(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
            adminid=cursor.fetchone()[0]
            if adminid:
                cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where added_by=%s and itemid=uuid_to_bin(%s) ',[adminid,itemid])
                item_data=cursor.fetchone()
                cursor.close()
            else:
                flash('user not found')
                return redirect(url_for('additem'))
        except Exception as e:
            print(e)
            flash('could not fetch all items')
            return redirect(url_for('admindashboard'))
        else:
            if request.method=='POST':
                updateditem_name=request.form['title']
                updateditem_description=request.form['Description']
                updateditem_about=request.form['About_item']
                updateditem_quantity=request.form['quantity']
                updateditem_price=request.form['price']
                updateditem_category=request.form['category']
                updateditem_filedata=request.files['file']
                print(updateditem_filedata)
                print(updateditem_filedata.filename)
                filename=updateditem_filedata.filename
                if filename=='':
                    filename=item_data[7]
                else:
                    if updateditem_filedata and filename:
                        if not allowed_file(filename):
                            flash('File type is not Allowed.pls give png,jpg,jpng,webp,gif')
                            return redirect(url_for('updateitem',itemid=itemid))
                        orig_secure=secure_filename(filename)
                        ext=os.path.splitext(orig_secure)[1] #anusha.txt
                        filename=genotp()+ext
                        save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                        try:
                            updateditem_filedata.save(save_path)
                            if item_data[7]:
                                remove_path=os.path.join(app.config['UPLOAD_FOLDER'],item_data[7])
                                os.remove(remove_path)
                        except Exception  as e:
                            flash('colud not store file data')
                            return redirect(url_for('updateitem',itemid=itemid))
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select adminid from admindata where admin_email=%s',[session.get('admin')])
                    adminid=cursor.fetchone()[0]
                    if adminid:
                        cursor.execute('update items set  itemname=%s,item_desc=%s,item_about=%s,price=%s,quantity=%s,category=%s,item_img=%s where added_by=%s and itemid=uuid_to_bin(%s)',[updateditem_name,updateditem_description,updateditem_about,updateditem_price,updateditem_quantity,updateditem_category,filename,adminid,itemid])
                        mydb.commit()
                        cursor.close()
                    else:
                        flash('user not found')
                        return redirect(url_for('updateitem',itemid=itemid))
                except Exception as e:
                    print(e)
                    flash('could not updateditem')
                    return redirect(url_for('updateitem',itemid=itemid))
                else:
                    flash('item updated successfully')
                    return redirect(url_for('updateitem',itemid=itemid))
                
            return render_template('updateitem.html',item_data=item_data)
    else:
        flash('pls login viewallitems')
        return redirect(url_for('adminlogin'))
@app.route('/adminprofileupadte',methods=['GET','POST'])
def adminprofileupdate():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select adminid,adminname,admin_phoneno,admin_address,admin_imgdata from admindata where admin_email=%s',[session.get('admin')])
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('could not fetch admindetails')
            return redirect(url_for('admindashboard'))
        else:
            if request.method=='POST':
                updated_adminname=request.form['adminname']
                updated_adminaddress=request.form['address']
                updated_adminphone=request.form['ph_no']
                updated_adminprofile=request.files['file']
                print(updated_adminprofile)
                filename=updated_adminprofile.filename
                if filename=='' or filename==None:
                    filename=admin_data[4]
                else:
                    if updated_adminprofile and filename:
                        if not allowed_file(filename):
                            flash('File type is not Allowed.pls give png,jpg,jpng,webp,gif')
                            return redirect(url_for('adminprofileupdate'))
                        orig_secure=secure_filename(filename)
                        ext=os.path.splitext(orig_secure)[1] #anusha.txt
                        filename=genotp()+ext
                        save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                        try:
                            updated_adminprofile.save(save_path)
                            if admin_data[4]:
                                remove_path=os.path.join(app.config['UPLOAD_FOLDER'],admin_data[4])
                                os.remove(remove_path)
                        except Exception  as e:
                            flash('colud not store file data')
                            return redirect(url_for('adminprofileupdate'))
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('update admindata set  adminname=%s,admin_address=%s,admin_phoneno=%s,admin_imgdata=%s where adminid=%s',[updated_adminname,updated_adminaddress,updated_adminphone,filename,admin_data[0]])
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash('could not update admin profile')
                    return redirect(url_for('adminprofileupdate'))
                else:
                    flash('admin profile  updated successfully')
                    return redirect(url_for('adminprofileupdate'))
            return render_template('adminupdate.html',admin_details=admin_data)         
    else:
        flash('pls login viewallitems')
        return redirect(url_for('adminlogin'))
@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('adminlogin'))
    else:
        flash('pls login to logout')
        return redirect(url_for('adminlogin'))
@app.route('/usercreate',methods=['GET','POST'])
def usercreate():
    if request.method=='POST':
        user_name=request.form['name'].strip()
        user_email=request.form['email'].strip()
        user_address=request.form['address'].strip()
        user_password=request.form['password'].strip()
        user_phone=request.form['phone_no']
        user_gender=request.form['usergender']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s ',[user_email])
            email_count=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Could not verify user')
            return redirect(url_for('usercreate'))
        else:
            if email_count[0]==0:
                gotp=genotp()
                userdata={'user_username':user_name,'user_useremail':user_email,'user_address':user_address,'user_userpassword':user_password,'user_phone':user_phone,'user_gender':user_gender,'user_otp':gotp}
                subject=f'User registration verification'
                body=f'use the otp for verification {gotp}'
                send_mail(to=user_email,subject=subject,body=body)
                flash('OTP has been sent to given mail')
                return redirect(url_for('userotpverify',userdata=endata(userdata)))
            elif email_count[0]==1:
                flash('email already existed')
                return redirect(url_for('usercreate'))
            else:
                flash('Email not verified')
    return render_template('usersignup.html')
@app.route('/userotpverify/<userdata>',methods=['GET','POST'])
def userotpverify(userdata):
    try:
        user_details=dndata(userdata)
    except Exception as e:
        flash('could not verify otp')
        return redirect(url_for('userotpverify',userdata=userdata))
    else:
        if request.method=='POST':
            userotp=request.form['otp']
            if userotp==user_details['user_otp']:
                hash_password=bcrypt.generate_password_hash(user_details['user_userpassword'])
                print(hash_password)
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('insert into userdata(userid,username,useremail,password,useraddress,usergender,userphone) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s)',[user_details['user_username'],user_details['user_useremail'],hash_password,user_details['user_address'],user_details['user_gender'],user_details['user_phone']])
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash('Colud not store user details')
                    return redirect(url_for('userotpverify',userdata=userdata))
                else:
                    flash('user details successfully stored')
                    return redirect(url_for('userlogin'))
            else:
                flash('Invalid otp')
                return redirect(url_for('userotpverify',userdata=userdata))
        return render_template('userotp.html')
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if request.method=='POST':
        login_email=request.form['email']
        login_password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s ',[login_email])
            email_count=cursor.fetchone()
            if email_count[0]==1:
                cursor.execute('select password from userdata where useremail=%s',[login_email])
                stored_password=cursor.fetchone()[0]
                if bcrypt.check_password_hash(stored_password,login_password):
                    print(session)
                    session['user']=login_email
                    if not session.get(login_email):
                        session[login_email]={}
                    print(session)
                    return redirect(url_for('index'))
                else:
                    flash('invalid password')
                    return redirect(url_for('userlogin'))
            elif email_count[0]==0:
                flash('No Email found')
                return redirect(url_for('userlogin'))
        except Exception as e:
            print(e)
            flash('Could not verify user')
            return redirect(url_for('userlogin'))
    return render_template('userlogin.html')
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('userlogin'))
    else:
        flash('pls login to logout')
        return redirect(url_for('userlogin'))
@app.route('/addcart/<uuid:itemid>')
def addcart(itemid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where itemid=uuid_to_bin(%s) ',[str(itemid)])
            item_data=cursor.fetchone()
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not fetch all items')
            return redirect(url_for('index'))
        else:
            print(session)
            if itemid not in session[session.get('user')]:
                session[session.get('user')][itemid]=[item_data[1],1,item_data[4],item_data[5],item_data[6],item_data[7]]
                session.modified=True
                print(session)
                flash('Item added to cart')
                return redirect(url_for('index'))
            else:
                session[session.get('user')][itemid][1]+=1
                flash('Item already in cart')
                return redirect(url_for('index'))       
    else:
        flash('pls login to addcart')
        return redirect(url_for('userlogin'))
@app.route('/viewcart')
def viewcart():
    if session.get('user'):
        if 'single_buy' in session:
            session.pop('single_buy')
            session.modified=True
        cart=session[session.get('user')]
      
        if not cart:
            flash('No items in cart')
            return redirect(url_for('index'))
        subtotal=0
        items_data=[]
        for i,j in cart.items():
            itemid=i
            item_name=j[0]
            item_price=float(j[2])
            item_quantity=int(j[1])
            item_category=j[4]
            item_imgname=j[5]
            subtotal=subtotal+item_price*item_quantity
            items_data.append([itemid,item_name,item_price,item_quantity,item_category,item_imgname])
        delivery=40
        tax=round(subtotal*0.05,2)
        grand_total=subtotal+delivery+tax
        return render_template('cart.html',delivery=delivery,tax=tax,grand_total=grand_total,subtotal=subtotal,items_data=items_data)
    else:
        flash('pls login to view cart items')
        return redirect(url_for('userlogin'))
@app.route('/updatecart/<uuid:itemid>',methods=['POST'])
def updatecart(itemid):
    if session.get('user'):
        try:
            updated_quantity=int(request.form['quantity'])
            if itemid  in session[session.get('user')]:
                session[session.get('user')][itemid][1]=updated_quantity
                session.modified=True
                print(session)
                flash('Item updated to cart')
                return redirect(url_for('viewcart'))
            else:
                
                flash('Item not in cart')
                return redirect(url_for('viewcart'))   
        except Exception as e:
            print(e)
            flash('could not update cart')
            return redirect(url_for('viewcart'))    
    else:
        flash('pls login to update cart')
        return redirect(url_for('userlogin'))
@app.route('/removecart/<uuid:itemid>')
def removecart(itemid):
    if session.get('user'):
        try:
            if itemid  in session[session.get('user')]:
                session[session.get('user')].pop(itemid)
                session.modified=True
                print(session)
                flash('Item removed from cart')
                return redirect(url_for('viewcart'))
            else: 
                flash('Item not in cart')
                return redirect(url_for('viewcart'))   
        except Exception as e:
            print(e)
            flash('could not removecart')
            return redirect(url_for('viewcart'))    
    else:
        flash('pls login to remove cart')
        return redirect(url_for('userlogin'))
@app.route('/pay_cart',methods=['GET','POST'])
def pay_cart():
    if not session.get('user'):
        flash('pls login buy cart items')
        return redirect(url_for('userlogin'))
    try:
        #fetch all the cart items 
        cart=session.get(session.get('user'),{})
        #only use single_buy if explicitly coming from buy now 
        cart_mode=''
        if request.args.get('type')=='single':
            cart=session.get('single_buy',{})
            cart_mode='single'
        else:
            if 'single_buy' in session:
                session.pop('single_buy')
                session.modified=True
                cart_mode='cart'
        print(cart)
        if not cart:
            flash('Your cart is empty')
            return redirect(url_for('index'))
        subtotal=0
        items_data=[]
        for i,j in cart.items():
            itemid=i
            item_name=j[0]
            item_price=float(j[2])
            item_quantity=int(j[1])
            item_category=j[4]
            item_imgname=j[5]
            amount=item_price*item_quantity
            subtotal=subtotal+item_price*item_quantity
            items_data.append([itemid,item_name,item_price,item_quantity,item_category,item_imgname,amount])
        delivery=40
        tax=round(subtotal*0.05,2)
        grand_total=subtotal+delivery+tax
        razorpay_amount=int(grand_total*100) #converted to paise
        #create razorpay order
        order=client.order.create({
            "amount":razorpay_amount,
            "currency":'INR',
            "receipt":f"{session.get('user')}",
            "payment_capture":"1"
        })
        print('created an order:',order)
        return render_template('pay.html',order=order,cart_items=items_data,items_total=subtotal,delivery=delivery,tax=tax,grand_total=grand_total,cart_mode=cart_mode)
    except Exception as e:
        print(e)
        flash('payment failed')
        return redirect(url_for('index'))

@app.route('/success_cart',methods=['POST'])
def success_cart():
    try:
        payment_id= request.form['razorpay_payment_id']
        order_id=request.form['razorpay_order_id']
        signature=request.form['razorpay_signature']
        amount=float(request.form['grand_total'])
        mode=request.form['mode']
        #verify payment signature
        params_dict={
            'razorpay_order_id':order_id,
            'razorpay_payment_id':payment_id,
            'razorpay_signature':signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            print(e)
            flash('payment failed')
            return redirect(url_for('home'))
        
        if mode=='single':
            cart=session.get('single_buy',{})
        else:
            if 'single_buy' in session:
                session.pop('single_buy')
                session.modified=True
            cart=session.get(session.get('user'),{})

        if not cart:
            flash('your cart is empty')
            redirect(url_for('index'))
        items_total=sum(float(v[1]) * int(v[2]) for  v in cart.values())
        delivery=40
        tax=round(items_total *0.05,2)
        grand_total=items_total+delivery+tax
        print(amount,grand_total)
        if amount==grand_total:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                user=cursor.fetchone()[0]
                cursor.execute('insert into orders(razorpay_ordid,razorpay_payment,userid,total_amount,delivery,tax,grand_total) values(%s,%s,%s,%s,%s,%s,%s)',[order_id,payment_id,user,items_total,delivery,tax,grand_total])
                order_table_id=cursor.lastrowid
                insert_item='''insert into order_items(orderid,itemid,item_name,item_price,item_quantity,subtotal,item_category,item_filename) values(%s,uuid_to_bin(%s),%s,%s,%s,%s,%s,%s)'''
                for i,j in cart.items():
                    itemid=i
                    item_name=j[0]
                    item_price=float(j[2])
                    item_quantity=int(j[1])
                    item_category=j[4]
                    item_imgname=j[5]
                    amount=item_price*item_quantity
                    cursor.execute(insert_item,[order_table_id,str(itemid),item_name,item_price,item_quantity,amount,item_category,item_imgname])
                mydb.commit()
                cursor.close()
            except Exception as e:
                app.logger.exception(f'Error order stoagre:{e}')
                flash('colud not order details')
                return redirect(url_for('pay_cart'))
            
           
            #-------remove temp single item data---
            if mode=='single':
                if 'single_buy' in session:
                    session.pop('single_buy')
                    session.modified=True
            session[session.get('user')]={}
            flash('payment successfull')
            return redirect(url_for('index'))
        else:
            flash('Amount invalid')
            return redirect(url_for('index'))

    except Exception as  e:
        app.logger.exception('Payment verification failed')
        flash('payment failed')
        return redirect(url_for('index'))
@app.route('/myorders')
def myorders():
    if not session.get('user'):
        flash('pls login view orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
    except Exception as  e:
        app.logger.exeception('user not found')
        flash('could not verify user')
        return redirect(url_for('index'))
    else:
        if user:
            cursor.execute('select * from orders where userid=%s order by created_at desc',[user])
            order_data=cursor.fetchall()
            cursor.close()
            return render_template('myorders.html',order_data=order_data)
        else:
            flash('user not found')
            return redirect(url_for('home'))
@app.route('/myorder_details/<ordid>')
def myorder_details(ordid):
    if not session.get('user'):
        flash('pls login view orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
    except Exception as  e:
        app.logger.exception('user not found')
        flash('could not verify user')
        return redirect(url_for('index'))
    else:
        if user:
            cursor.execute('select * from orders where userid=%s and orderid=%s',[user,ordid])
            order_data=cursor.fetchone()
            cursor.execute('select order_detailsid,orderid,bin_to_uuid(itemid),item_name,item_price,item_quantity,subtotal,item_category,item_filename from order_items where orderid=%s',[ordid])
            orders_itemsdata=cursor.fetchall()
            cursor.close()
            return render_template('order_details.html',order_data=order_data,orders_itemsdata=orders_itemsdata)
        else:
            flash('user not found')
            return redirect(url_for('home'))
@app.route('/buy_now',methods=['POST'])
def buy_now():
    if session.get('user'):
        itemid=request.form['itemid']
        print(session)
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where itemid=uuid_to_bin(%s) ',[itemid])
            item_data=cursor.fetchone()
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not fetch item')
            return redirect(url_for('index'))
        else:
            session['single_buy']={itemid:[item_data[1],1,item_data[4],item_data[5],item_data[6],item_data[7]]}
            session.modified=True
            print(session)
            flash('Item added to cart')
            return redirect(url_for('pay_cart',type='single'))
    else:
        flash('pls login to buy')
        return redirect(url_for('userlogin'))
@app.route('/get_invoice/<int:ord_id>')
def get_invoice(ord_id):
    if not session.get('user'):
        flash('pls login first')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
    except Exception as  e:
        app.logger.exception('user not found')
        flash('could not verify user')
        return redirect(url_for('index'))
    else:
        if user:
            cursor.execute('select * from orders where userid=%s and orderid=%s',[user,ord_id])
            order_data=cursor.fetchone()
            cursor.execute('select order_detailsid,orderid,bin_to_uuid(itemid),item_name,item_price,item_quantity,subtotal,item_category,item_filename from order_items where orderid=%s',[ord_id])
            orders_itemsdata=cursor.fetchall()
            cursor.close()
            html=render_template('invoice.html',order_data=order_data,orders_itemsdata=orders_itemsdata)
            #generate pdf
            pdf=BytesIO()
            pisa_status=pisa.CreatePDF(html,dest=pdf)
            if pisa_status.err:
                return 'Error generating pdf'
            response = make_response(pdf.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=invoice_{ord_id}.pdf'
            return response
@app.route('/category/<ctype>')
def category(ctype):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where category=%s ',[ctype])
        items_data=cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch all items')
        return redirect(url_for('index'))
    else:
        return render_template('dashboard.html',allitems_data=items_data)
@app.route('/descitem/<itemid>')
def descitem(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where itemid=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(e)
        flash('could not fetch item details')
        return redirect(url_for('index'))
    else:
        return render_template('desc.html',storeditem_data=item_data)
@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            rating=request.form['rating']
            review_text=request.form['review_text']
            try:
                cursor=mydb.cursor()
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                userid=cursor.fetchone()[0]
                cursor.execute('insert into reviews(r_text,rating,itemid,userid) value(%s,%s,uuid_to_bin(%s),%s)',[review_text,rating,itemid,userid])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('could not addreview')
                return redirect(url_for('addreview'))
            else:
                flash('review added successfully')

        return render_template('addreview.html',itemid=itemid)
    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))
@app.route('/usersearch',methods=['POST'])
def usersearch():
    searchdata=request.form['q']
    strg=['A-Za-z0-9']
    pattern=re.compile(f'^{strg}',re.IGNORECASE)
    if pattern.match(searchdata):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute(' select bin_to_uuid(itemid),itemname,item_desc,item_about,price,quantity,category,item_img from items where itemname like %s or item_desc like %s or price like %s or category like %s',[searchdata+'%',searchdata+'%',searchdata+'%',searchdata+'%'])
            allitem_data=cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not fetch item details')
            return redirect(url_for('index'))
        else:
            return render_template('dashboard.html',allitems_data=allitem_data)

    else:
        flash('invalid search')
        return redirect(url_for('index'))
    
if __name__=='__main__':
    app.run(use_reloader=True,debug=True)