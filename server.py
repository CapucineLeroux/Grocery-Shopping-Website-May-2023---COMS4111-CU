
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


# Connecting to database
DATABASEURI = "sqlite:///fast_food_database.db"


# This line creates a database engine that knows how to connect to the URI above.
engine = create_engine(DATABASEURI, future=True)

# Initialize the current user_id, the current store_id and the current shopping_cart
CURRENT_USER_ID = None # needed when logged to a user's account
CURRENT_STORE_ID = None # needed when consulting a store page
CURRENT_SHOPPING_CART = {'items':[]} 
CURRENT_ORDER_ID = None


# Set up for requests
@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request 
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request.

    The variable g is globally accessible.
    """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't, the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


# Pages
@app.route('/')
def index():

    # reset user_id
    global CURRENT_USER_ID
    CURRENT_USER_ID = None
    print("CURRENT_USER_ID = "+str(CURRENT_USER_ID))

    return render_template("index.html")

@app.route('/log_in')
def log_in():

    # reset user_id
    global CURRENT_USER_ID
    CURRENT_USER_ID = None
    print("CURRENT_USER_ID = "+str(CURRENT_USER_ID))

    return render_template("log_in.html")

@app.route('/sign_up')
def sign_up():
    return render_template("sign_up.html")

@app.route('/submit_login', methods=['POST'])
def submit_login():

    # accessing form inputs from user
    username = request.form['username']
    password = request.form['password']
    print("\nLogin:\nUsername = "+str(username)+"\nPassword = "+str(password)+"\n")

    # update the current_user_id before logging in 
    params = {}
    params["new_username"] = username
    params["new_password"] = password
    global CURRENT_USER_ID
    CURRENT_USER_ID = g.conn.execute(text('select min(user_id) from users where username=:new_username and password=:new_password'), params).scalar()
    print("\nUpdated CURRENT_USER_ID to "+str(CURRENT_USER_ID))
    
    if CURRENT_USER_ID:
        return redirect('/grocery_stores')
    else:
        return redirect('/log_in_error')

@app.route('/log_in_error')
def log_in_error():
    return render_template("log_in_error.html")

@app.route('/user_profile')
def user_profile():

    # get user info
    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    select_query = "SELECT * from users where user_id=:user_id"
    cursor = g.conn.execute(text(select_query),params)
    record = cursor.fetchone()
    cursor.close()
    user_information = {'user_id': record[0], 'first_name':record[1], 'last_name':record[2], 'username': record[3], 'password': record[4], 'phone': record[5], 'email': record[6], 'payment_method_set_id':record[7], 'delivery_address_set_id':record[8]}
    print("USER_PROFILE - user_information")
    print(user_information)

    # get addresses
    user_information['addresses'] = []
    params["delivery_address_set_id"] = user_information['delivery_address_set_id']
    select_query = "SELECT * from delivery_address_sets where delivery_address_set_id=:delivery_address_set_id"
    cursor = g.conn.execute(text(select_query),params)
    for record in cursor:
        params["address_id"] = record[1]
        select_query = "SELECT * from delivery_addresses where address_id=:address_id"
        address_record = g.conn.execute(text(select_query),params).fetchone()
        user_information['addresses'].append({'addresses_id': address_record[0], 'first_name':address_record[1], 'last_name':address_record[2], 'street_info': address_record[3], 'city': address_record[4], 'country': address_record[5], 'zip': address_record[6]})
    cursor.close()
    print("USER_PROFILE - user_information[addresses]")
    print(user_information['addresses'])

    # get payments
    user_information['payments'] = []
    params["payment_method_set_id"] = user_information["payment_method_set_id"]
    select_query = "SELECT * from payment_method_sets where payment_method_set_id=:payment_method_set_id"
    cursor = g.conn.execute(text(select_query),params)
    for record in cursor:
        params["payment_id"] = record[1]
        select_query = "SELECT * from payment_methods where payment_id=:payment_id"
        payment_record = g.conn.execute(text(select_query),params).fetchone()
        user_information['payments'].append({'payment_id': payment_record[0], 'first_name':payment_record[1], 'last_name':payment_record[2], 'card_number': payment_record[3], 'exp': payment_record[4], 'cvv': payment_record[5], 'zip': payment_record[6]})
    cursor.close()
    print("USER_PROFILE - user_information[payments]")
    print(user_information['payments'])

    #get orders
    user_information['orders'] = []
    select_query = "SELECT * from orders where user_id=:user_id"
    cursor = g.conn.execute(text(select_query),params)
    for record in cursor:
        params["order_id"] = record[0]
        select_query = "SELECT * from orders where order_id=:order_id"
        order_record = g.conn.execute(text(select_query),params).fetchone()
        new_order_element = {'order_id': order_record[0],'user_id': order_record[1],'arrival_date': order_record[2],'order_date': order_record[3],'set_id': order_record[6]}
        params["set_id"] =  order_record[6]
        select_query = "select sum(sub.full_price) from (select s.grocery_item_set_id, g.item_id, g.store_id, s.quantity_ordered*g.price_per_unit as full_price from grocery_item_sets s, grocery_items g where s.item_id=g.item_id and s.store_id=g.store_id and s.grocery_item_set_id=:set_id) as sub"
        total_price = g.conn.execute(text(select_query),params).scalar()
        new_order_element["total_price"] = total_price
        user_information['orders'].append(new_order_element)
    cursor.close()
    print("USER_PROFILE - user_information[orders]")
    print(user_information['orders'])

    return render_template("user_profile.html", user_information=user_information)

@app.route('/go_to_item', methods=['POST'])
def go_to_item():
    global CURRENT_ORDER_ID
    CURRENT_ORDER_ID = request.form['order_id']
    print("CURRENT_ORDER_ID = "+str(CURRENT_ORDER_ID))

    return redirect('/order_items')

@app.route('/order_items')
def order_items():
    global CURRENT_ORDER_ID
    params = {}
    params["order_id"] = CURRENT_ORDER_ID

    # get the order infos
    select_query = 'SELECT * from orders where order_id=:order_id'
    cursor = g.conn.execute(text(select_query),params)
    record = cursor.fetchone()
    cursor.close()
    params["grocery_item_set_id"] = record[6]

    # get the items infos
    select_query = 'SELECT * from grocery_item_sets where grocery_item_set_id=:grocery_item_set_id'
    cursor = g.conn.execute(text(select_query),params)

    items = []
    for record in cursor:
        params["item_id"] = record[1]
        params["store_id"] = record[2]
        select_query = 'SELECT * from grocery_items where item_id=:item_id and store_id=:store_id'
        cursor1 = g.conn.execute(text(select_query),params)
        record1 = cursor1.fetchone()
        cursor1.close()
        items.append({'name':record1[2],'price':record1[3],'ms_unit':record1[4],'av_unit':record1[5],'quantity_ordered':record[3],'full_price':record[3]*record1[3]})
    cursor.close()
    return render_template("order_items.html", items=items)

@app.route('/user_page')
def user_page():
    global CURRENT_ORDER_ID 
    CURRENT_ORDER_ID = None
    return redirect("/user_profile")

@app.route('/grocery_stores')
def grocery_stores():

    # reset store_id
    global CURRENT_STORE_ID
    CURRENT_STORE_ID = None
    print("CURRENT_STORE_ID = "+str(CURRENT_STORE_ID))

    select_query = "SELECT store_id, name, address from grocery_stores"
    cursor = g.conn.execute(text(select_query))
    grocery_stores = []
    for result in cursor:
        grocery_stores.append({'store_id':result[0], 'name':result[1], 'address':result[2]}) 
    cursor.close()

    return render_template("grocery_stores.html", grocery_stores=grocery_stores)

@app.route('/submit_user_info', methods=['POST'])
def submit_user_info():

    # extract user infos from the form
    user_id = g.conn.execute(text('select max(user_id) from users')).scalar() + 1
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    username = request.form['username']
    password = request.form['password']
    phone = request.form['phone'] if request.form['phone'] else None
    email = request.form['email'] if request.form['email'] and ('@' in request.form['email']) else None

    print("\nUser Information:\nUser ID = "+str(user_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nUsername = "+str(username)+"\nPassword = "+str(password)+"\nPhone = "+str(phone)+"\nEmail = "+str(email)+"\n")

    # add the user signup infos to the users table
    params = {}
    params["new_user_id"] = user_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_username"] = username
    params["new_password"] = password
    params["new_phone"] = phone
    params["new_email"] = email
    g.conn.execute(text('INSERT INTO users VALUES (:new_user_id,:new_first_name,:new_last_name,:new_username,:new_password,:new_phone,:new_email)'), params)
    g.conn.commit()

    # remember the user_id
    global CURRENT_USER_ID
    CURRENT_USER_ID = user_id

    return redirect('/sign_up_address')

@app.route('/sign_up_address')
def sign_up_address():
    print("\nOpening sign_up_address\n")
    return render_template("sign_up_address.html")

@app.route('/submit_address', methods=['POST'])
def submit_address():
    print("\nStarting action submit_address\n")

    # extract user address from the form
    address_id = g.conn.execute(text('select max(address_id) from delivery_addresses')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_delivery_address_set = g.conn.execute(text('select delivery_address_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_delivery_address_set:
        delivery_address_set_id = has_a_delivery_address_set
    else:
        delivery_address_set_id = g.conn.execute(text('select max(delivery_address_set_id) from delivery_address_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    street_name_and_number = request.form['street_name_and_number']
    city = request.form['city']
    country = request.form['country']
    zip_code = request.form['zip_code']
    print("\nAddress Information:\nAddress ID = "+str(address_id)+"\nDelivery Address Set ID = "+str(delivery_address_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nStreet Name and Number = "+str(street_name_and_number)+"\nCity = "+str(city)+"\nCountry = "+str(country)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user address the delivery_addresses table 
    params["new_address_id"] = address_id
    params["new_delivery_address_set_id"] = delivery_address_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_street_name_and_number"] = street_name_and_number
    params["new_city"] = city
    params["new_country"] = country
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO delivery_addresses VALUES (:new_address_id,:new_first_name,:new_last_name,:new_street_name_and_number,:new_city,:new_country,:new_zip_code)'), params)
    g.conn.commit()
    # create a new delivery_address_sets row
    g.conn.execute(text('INSERT INTO delivery_address_sets VALUES (:new_delivery_address_set_id,:new_address_id)'), params)
    g.conn.commit()
    # update the users table with the new delivery_address_set_id if needed
    g.conn.execute(text('UPDATE users SET delivery_address_set_id = :new_delivery_address_set_id WHERE user_id =:user_id'), params)
    g.conn.commit()

    print("\nFinishing action submit_address\n")

    return redirect('/sign_up_payment')

@app.route('/edit_address')
def edit_address():
    return render_template("edit_address.html")

@app.route('/edit_addresses', methods=['POST'])
def edit_addresses():

    # extract user address from the form
    address_id = g.conn.execute(text('select max(address_id) from delivery_addresses')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_delivery_address_set = g.conn.execute(text('select delivery_address_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_delivery_address_set:
        delivery_address_set_id = has_a_delivery_address_set
    else:
        delivery_address_set_id = g.conn.execute(text('select max(delivery_address_set_id) from delivery_address_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    street_name_and_number = request.form['street_name_and_number']
    city = request.form['city']
    country = request.form['country']
    zip_code = request.form['zip_code']
    print("\nAddress Information:\nAddress ID = "+str(address_id)+"\nDelivery Address Set ID = "+str(delivery_address_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nStreet Name and Number = "+str(street_name_and_number)+"\nCity = "+str(city)+"\nCountry = "+str(country)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user address the delivery_addresses table 
    params["new_address_id"] = address_id
    params["new_delivery_address_set_id"] = delivery_address_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_street_name_and_number"] = street_name_and_number
    params["new_city"] = city
    params["new_country"] = country
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO delivery_addresses VALUES (:new_address_id,:new_first_name,:new_last_name,:new_street_name_and_number,:new_city,:new_country,:new_zip_code)'), params)
    g.conn.commit()
    # create a new delivery_address_sets row
    g.conn.execute(text('INSERT INTO delivery_address_sets VALUES (:new_delivery_address_set_id,:new_address_id)'), params)
    g.conn.commit()
    # update the users table with the new delivery_address_set_id if needed
    g.conn.execute(text('UPDATE users SET delivery_address_set_id = :new_delivery_address_set_id WHERE user_id =:user_id'), params)
    g.conn.commit()

    return redirect("/user_profile")

@app.route('/sign_up_payment')
def sign_up_payment():
    return render_template("sign_up_payment.html")

@app.route('/submit_payment', methods=['POST'])
def submit_payment():

    # extract user payment from the form
    payment_id = g.conn.execute(text('select max(payment_id) from payment_methods')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_payment_method_set = g.conn.execute(text('select payment_method_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_payment_method_set:
        payment_method_set_id = has_a_payment_method_set
    else:
        payment_method_set_id = g.conn.execute(text('select max(payment_method_set_id) from payment_method_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    card_number = request.form['card_number']
    expiration_date = request.form['expiration_date']
    cvv = request.form['cvv']
    zip_code = request.form['zip_code']
    print("\nPayment Information:\nPayment ID = "+str(payment_id)+"\nPayment Method Set ID = "+str(payment_method_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nCard Number = "+str(card_number)+"\nExpiration Date = "+str(expiration_date)+"\nCVV = "+str(cvv)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user payment the payment_methods table 
    params["new_payment_id"] = payment_id
    params["new_payment_method_set_id"] = payment_method_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_card_number"] = card_number
    params["new_expiration_date"] = expiration_date
    params["new_cvv"] = cvv
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO payment_methods VALUES (:new_payment_id,:new_first_name,:new_last_name,:new_card_number,:new_expiration_date,:new_cvv,:new_zip_code)'), params)
    g.conn.commit()
    # create a new payment_method_set_id row
    g.conn.execute(text('INSERT INTO payment_method_sets VALUES (:new_payment_method_set_id,:new_payment_id)'), params)
    g.conn.commit()
    # update the users table with the new payment_method_set_id
    g.conn.execute(text('UPDATE users SET payment_method_set_id = :new_payment_method_set_id WHERE user_id = :user_id'), params)
    g.conn.commit()

    return redirect('/sign_up_confirmation')

@app.route('/edit_payment')
def edit_payment():
    return render_template("edit_payment.html")

@app.route('/edit_payments', methods=['POST'])
def edit_payments():

    # extract user payment from the form
    payment_id = g.conn.execute(text('select max(payment_id) from payment_methods')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_payment_method_set = g.conn.execute(text('select payment_method_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_payment_method_set:
        payment_method_set_id = has_a_payment_method_set
    else:
        payment_method_set_id = g.conn.execute(text('select max(payment_method_set_id) from payment_method_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    card_number = request.form['card_number']
    expiration_date = request.form['expiration_date']
    cvv = request.form['cvv']
    zip_code = request.form['zip_code']
    print("\nPayment Information:\nPayment ID = "+str(payment_id)+"\nPayment Method Set ID = "+str(payment_method_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nCard Number = "+str(card_number)+"\nExpiration Date = "+str(expiration_date)+"\nCVV = "+str(cvv)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user payment the payment_methods table 
    params["new_payment_id"] = payment_id
    params["new_payment_method_set_id"] = payment_method_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_card_number"] = card_number
    params["new_expiration_date"] = expiration_date
    params["new_cvv"] = cvv
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO payment_methods VALUES (:new_payment_id,:new_first_name,:new_last_name,:new_card_number,:new_expiration_date,:new_cvv,:new_zip_code)'), params)
    g.conn.commit()
    # create a new payment_method_set_id row
    g.conn.execute(text('INSERT INTO payment_method_sets VALUES (:new_payment_method_set_id,:new_payment_id)'), params)
    g.conn.commit()
    # update the users table with the new payment_method_set_id
    g.conn.execute(text('UPDATE users SET payment_method_set_id = :new_payment_method_set_id WHERE user_id = :user_id'), params)
    g.conn.commit()

    return redirect('/user_profile')


@app.route('/sign_up_confirmation')
def sign_up_confirmation():

    # reset current_user_id (because we are going back to home page)
    global CURRENT_USER_ID
    CURRENT_USER_ID = None

    return render_template("sign_up_confirmation.html")

@app.route('/go_to_store', methods=['POST'])
def go_to_store():

    # remember the store_id
    global CURRENT_STORE_ID
    CURRENT_STORE_ID = request.form['store_id']
    print("CURRENT_STORE_ID = "+str(CURRENT_STORE_ID))

    return redirect('/store_page')

@app.route('/store_page')
def store_page():

    # get the right store_id
    global CURRENT_STORE_ID
    params = {}
    params["store_id"] = CURRENT_STORE_ID

    # get the store's contact information
    select_query = 'SELECT * from grocery_stores where store_id=:store_id order by store_id'
    cursor = g.conn.execute(text(select_query),params)
    record = cursor.fetchone()
    cursor.close()
    grocery_store = {'store_id':record[0],'name':record[1],'address':record[2],'phone':record[3],'email':record[4]}

    # get the store's items
    grocery_store['items'] = []
    select_query = 'SELECT * from grocery_items where store_id=:store_id order by item_id'
    cursor = g.conn.execute(text(select_query),params)
    for record in cursor:
        grocery_store['items'].append({'item_id':record[0],'name':record[2],'price_per_unit':record[3],'measurement_unit':record[4],'available_quantity':record[5]})
    cursor.close()
    
    return render_template("store_page.html", grocery_store=grocery_store)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():

    # get the wanted quantity and the item info
    wanted_quantity = int(request.form['wanted_quantity'])
    item = eval(request.form['item'])
    print("Wanted quantity = "+str(wanted_quantity)+" from item: "+str(item)+" added to shopping cart.")

    # remove this quantity from the item available quantity in the database
    item['available_quantity'] -= wanted_quantity
    params = {}
    global CURRENT_STORE_ID
    params["store_id"] = CURRENT_STORE_ID
    params["item_id"] = item['item_id']
    params["new_available_quantity"] = item['available_quantity']
    g.conn.execute(text('UPDATE grocery_items SET available_quantity=:new_available_quantity WHERE store_id=:store_id and item_id=:item_id'), params)
    g.conn.commit()

    # add to current shopping_cart
    global CURRENT_SHOPPING_CART
    new_element = {'store_id':CURRENT_STORE_ID,'item_id':item['item_id'],'wanted_quantity':wanted_quantity}
    for element in CURRENT_SHOPPING_CART['items']:
        if element['store_id'] == new_element['store_id'] and element['item_id'] == new_element['item_id']:
            element['wanted_quantity'] += new_element['wanted_quantity']
            break
    else:
        CURRENT_SHOPPING_CART['items'].append(new_element)
    print("The current shopping cart looks like this: "+str(CURRENT_SHOPPING_CART['items']))

    # redirect to the store page
    return redirect('/store_page')

@app.route('/shopping_cart')
def shopping_cart():

    # reset current store_id
    global CURRENT_STORE_ID
    CURRENT_STORE_ID = None

    # get the current shopping_cart
    global CURRENT_SHOPPING_CART

    # query item infos for each item of the shopping cart
    shopping_cart = {'items':[],'total_price':0}
    for item in CURRENT_SHOPPING_CART['items']:

        new_item = dict()
        
        # get the store's contact information
        params = {}
        params["store_id"] = item["store_id"]
        select_query = 'SELECT * from grocery_stores where store_id=:store_id order by store_id'
        cursor = g.conn.execute(text(select_query),params)
        record = cursor.fetchone()
        cursor.close()
        new_item['store'] = {'store_id':record[0],'name':record[1],'address':record[2],'phone':record[3],'email':record[4]}

        # get the item info
        params["item_id"] = item["item_id"]
        select_query = 'SELECT * from grocery_items where store_id=:store_id and item_id=:item_id'
        cursor = g.conn.execute(text(select_query),params)
        record = cursor.fetchone()
        cursor.close()
        price = item["wanted_quantity"] * record[3]
        new_item['item'] = {'item_id':item["item_id"],'wanted_quantity':item["wanted_quantity"],'name':record[2],'price_per_unit':record[3],'price':price}

        shopping_cart['items'].append(new_item)
        shopping_cart['total_price'] += price

    return render_template("shopping_cart.html",shopping_cart=shopping_cart)


@app.route('/delete_from_cart', methods=['POST'])
def delete_from_cart():

    # get the store_id and the item_id of the to-be-deleted item
    store_id = int(request.form['store_id'])
    item_id = int(request.form['item_id'])
    wanted_quantity = int(request.form['wanted_quantity'])

    # remove it from the global shopping_cart variable
    global CURRENT_SHOPPING_CART
    for i in range (len(CURRENT_SHOPPING_CART['items'])):
        element = CURRENT_SHOPPING_CART['items'][i]
        if int(element['store_id']) == store_id and int(element['item_id']) == item_id:
            del CURRENT_SHOPPING_CART['items'][i]
            break
    print("The current shopping cart looks like this: "+str(CURRENT_SHOPPING_CART['items']))

    # update the available quantity in the database
    params = {}
    params["store_id"] = store_id
    params["item_id"] = item_id
    old_available_quantity = g.conn.execute(text('select available_quantity from grocery_items where item_id=:item_id and store_id=:store_id'),params).scalar()
    params["new_available_quantity"] = old_available_quantity + wanted_quantity
    g.conn.execute(text('UPDATE grocery_items SET available_quantity=:new_available_quantity WHERE store_id=:store_id and item_id=:item_id'), params)
    g.conn.commit()

    # redirect to the shopping cart
    return redirect('/shopping_cart')

@app.route('/order_address')
def order_address():

    # get saved addresses
    addresses = []
    # find the user_id
    global CURRENT_USER_ID
    params = {'user_id':CURRENT_USER_ID}
    # find the id of the delivery_address_set
    delivery_address_set_id = g.conn.execute(text('select delivery_address_set_id from users where user_id=:user_id'),params).scalar()
    if delivery_address_set_id:
        # find the ids of the delivery_addresses in the set
        params["delivery_address_set_id"] = delivery_address_set_id
        select_query1 = 'SELECT address_id from delivery_address_sets where delivery_address_set_id=:delivery_address_set_id'
        cursor1 = g.conn.execute(text(select_query1),params)
        for record1 in cursor1:
            params["address_id"] = record1[0]
            select_query2 = 'SELECT * from delivery_addresses where address_id=:address_id'
            cursor2 = g.conn.execute(text(select_query2),params)
            record2 = cursor2.fetchone()
            addresses.append({'address_id':record2[0],'first_name':record2[1],'last_name':record2[2],'street_name_and_number':record2[3],'city':record2[4],'country':record2[5],'zip_code':record2[6]})
            cursor2.close()
        cursor1.close()

    return render_template("order_address.html",addresses=addresses)

@app.route('/confirm_order_address', methods=['POST'])
def confirm_order_address():

    # get the address_id
    global CURRENT_SHOPPING_CART
    CURRENT_SHOPPING_CART['address_id'] = int(request.form['address_id'])
    print("Chose address with id = "+str(CURRENT_SHOPPING_CART['address_id']))

    # redirect to the order payment
    return redirect('/order_payment')


@app.route('/submit_order_address', methods=['POST'])
def submit_order_address():

    # extract user address from the form
    address_id = g.conn.execute(text('select max(address_id) from delivery_addresses')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_delivery_address_set = g.conn.execute(text('select delivery_address_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_delivery_address_set:
        delivery_address_set_id = has_a_delivery_address_set
    else:
        delivery_address_set_id = g.conn.execute(text('select max(delivery_address_set_id) from delivery_address_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    street_name_and_number = request.form['street_name_and_number']
    city = request.form['city']
    country = request.form['country']
    zip_code = request.form['zip_code']
    print("\nAddress Information:\nAddress ID = "+str(address_id)+"\nDelivery Address Set ID = "+str(delivery_address_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nStreet Name and Number = "+str(street_name_and_number)+"\nCity = "+str(city)+"\nCountry = "+str(country)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user address the delivery_addresses table 
    params["new_address_id"] = address_id
    params["new_delivery_address_set_id"] = delivery_address_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_street_name_and_number"] = street_name_and_number
    params["new_city"] = city
    params["new_country"] = country
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO delivery_addresses VALUES (:new_address_id,:new_first_name,:new_last_name,:new_street_name_and_number,:new_city,:new_country,:new_zip_code)'), params)
    g.conn.commit()
    # create a new delivery_address_sets row
    g.conn.execute(text('INSERT INTO delivery_address_sets VALUES (:new_delivery_address_set_id,:new_address_id)'), params)
    g.conn.commit()
    # update the users table with the new delivery_address_set_id if needed
    g.conn.execute(text('UPDATE users SET delivery_address_set_id = :new_delivery_address_set_id WHERE user_id =:user_id'), params)
    g.conn.commit()

    # update the shopping_cart
    CURRENT_SHOPPING_CART['address_id'] = address_id
    print("Chose address with id = "+str(CURRENT_SHOPPING_CART['address_id']))

    # redirect to the order payment
    return redirect('/order_payment')

@app.route('/order_payment')
def order_payment():

    # get saved payments
    payments = []
    # find the user_id
    global CURRENT_USER_ID
    params = {'user_id':CURRENT_USER_ID}
    # find the id of the payment_method_set
    payment_method_set_id = g.conn.execute(text('select payment_method_set_id from users where user_id=:user_id'),params).scalar()
    if payment_method_set_id:
        # find the ids of the payment_methods in the set
        params["payment_method_set_id"] = payment_method_set_id
        select_query1 = 'SELECT payment_id from payment_method_sets where payment_method_set_id=:payment_method_set_id'
        cursor1 = g.conn.execute(text(select_query1),params)
        for record1 in cursor1:
            params["payment_id"] = record1[0]
            select_query2 = 'SELECT * from payment_methods where payment_id=:payment_id'
            cursor2 = g.conn.execute(text(select_query2),params)
            record2 = cursor2.fetchone()
            payments.append({'payment_id':record2[0],'first_name':record2[1],'last_name':record2[2],'card_number':record2[3],'expiration_date':record2[4],'cvv':record2[5],'zip_code':record2[6]})
            cursor2.close()
        cursor1.close()

    return render_template("order_payment.html",payments=payments)

@app.route('/confirm_order_payment', methods=['POST'])
def confirm_order_payment():

    # get the payment_id
    global CURRENT_SHOPPING_CART
    CURRENT_SHOPPING_CART['payment_id'] = int(request.form['payment_id'])
    print("Chose payment with id = "+str(CURRENT_SHOPPING_CART['payment_id']))

    # redirect to the order payment
    return redirect('/order_confirmation')

@app.route('/submit_order_payment', methods=['POST'])
def submit_order_payment():

    # extract user payment from the form
    payment_id = g.conn.execute(text('select max(payment_id) from payment_methods')).scalar() + 1

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    has_a_payment_method_set = g.conn.execute(text('select payment_method_set_id from users where user_id=:user_id'),params).scalar()
    if has_a_payment_method_set:
        payment_method_set_id = has_a_payment_method_set
    else:
        payment_method_set_id = g.conn.execute(text('select max(payment_method_set_id) from payment_method_sets')).scalar() + 1

    first_name = request.form['first_name']
    last_name = request.form['last_name']
    card_number = request.form['card_number']
    expiration_date = request.form['expiration_date']
    cvv = request.form['cvv']
    zip_code = request.form['zip_code']
    print("\nPayment Information:\nPayment ID = "+str(payment_id)+"\nPayment Method Set ID = "+str(payment_method_set_id)+"\nFirst Name = "+str(first_name)+"\nLast Name = "+str(last_name)+"\nCard Number = "+str(card_number)+"\nExpiration Date = "+str(expiration_date)+"\nCVV = "+str(cvv)+"\nZip Code = "+str(zip_code)+"\n")

    # add the user payment the payment_methods table 
    params["new_payment_id"] = payment_id
    params["new_payment_method_set_id"] = payment_method_set_id
    params["new_first_name"] = first_name
    params["new_last_name"] = last_name
    params["new_card_number"] = card_number
    params["new_expiration_date"] = expiration_date
    params["new_cvv"] = cvv
    params["new_zip_code"] = zip_code
    g.conn.execute(text('INSERT INTO payment_methods VALUES (:new_payment_id,:new_first_name,:new_last_name,:new_card_number,:new_expiration_date,:new_cvv,:new_zip_code)'), params)
    g.conn.commit()
    # create a new payment_method_set_id row
    g.conn.execute(text('INSERT INTO payment_method_sets VALUES (:new_payment_method_set_id,:new_payment_id)'), params)
    g.conn.commit()
    # update the users table with the new payment_method_set_id
    g.conn.execute(text('UPDATE users SET payment_method_set_id = :new_payment_method_set_id WHERE user_id = :user_id'), params)
    g.conn.commit()

    # update the shopping_cart
    CURRENT_SHOPPING_CART['payment_id'] = payment_id
    print("Chose payment with id = "+str(CURRENT_SHOPPING_CART['payment_id']))

    # redirect to the order payment
    return redirect('/order_confirmation')

@app.route('/order_confirmation')
def order_confirmation():

    global CURRENT_SHOPPING_CART
    # add this order to the database
    grocery_item_set_id = g.conn.execute(text('select max(grocery_item_set_id) from grocery_item_sets')).scalar() + 1
    params = {'grocery_item_set_id':grocery_item_set_id}

    # add set rows
    for item in CURRENT_SHOPPING_CART['items']:
        params['item_id'] = item['item_id']
        params['store_id'] = item['store_id']
        params['quantity_ordered'] = item['wanted_quantity']
        g.conn.execute(text('INSERT INTO grocery_item_sets VALUES (:grocery_item_set_id,:item_id,:store_id,:quantity_ordered)'), params)
        g.conn.commit()
    
    # add order
    order_id = g.conn.execute(text('select max(order_id) from orders')).scalar() + 1
    params['order_id'] = order_id
    global CURRENT_USER_ID
    params['user_id'] = CURRENT_USER_ID
    params['order_date'] = datetime.today().strftime('%Y-%m-%d')
    params['payment_id'] = CURRENT_SHOPPING_CART['payment_id']
    params['address_id'] = CURRENT_SHOPPING_CART['address_id']
    g.conn.execute(text('INSERT INTO orders VALUES (:order_id,:user_id,NULL,:order_date,:payment_id,:address_id,:grocery_item_set_id)'), params)
    g.conn.commit()

    # reset the shopping cart
    CURRENT_SHOPPING_CART = {'items':[]}
    return render_template("order_confirmation.html")

@app.route('/logout')
def logout():

    # reset user_id
    global CURRENT_USER_ID
    CURRENT_USER_ID = None
    print("CURRENT_USER_ID = "+str(CURRENT_USER_ID))

    #reset shopping cart
    global CURRENT_SHOPPING_CART
    CURRENT_SHOPPING_CART = {'items':[]} 
    print("CURRENT_SHOPPING_CART = "+str(CURRENT_SHOPPING_CART))

    #reset store id
    global CURRENT_STORE_ID
    CURRENT_STORE_ID = None
    print("CURRENT_STORE_ID = "+str(CURRENT_STORE_ID))

    return render_template("logout.html")

@app.route('/delete_address', methods=['POST'])
def delete_address():

    global CURRENT_USER_ID
    params={}
    params["address_id"] = int(request.form['address_id'])
    params["user_id"] = CURRENT_USER_ID
    params["delivery_address_set_id"] = g.conn.execute(text("select delivery_address_set_id from users where user_id=:user_id"),params).scalar()
    print(params)
    g.conn.execute(text("delete from delivery_address_sets where delivery_address_set_id=:delivery_address_set_id and address_id=:address_id"),params)
    g.conn.commit()

    return redirect('/user_profile')

@app.route('/delete_payment', methods=['POST'])
def delete_payment():

    global CURRENT_USER_ID
    params={}
    params["payment_id"] = int(request.form['payment_id'])
    params["user_id"] = CURRENT_USER_ID
    params["payment_method_set_id"] = g.conn.execute(text("select payment_method_set_id from users where user_id=:user_id"),params).scalar()
    print(params)
    g.conn.execute(text("delete from payment_method_sets where payment_method_set_id=:payment_method_set_id and payment_id=:payment_id"),params)
    g.conn.commit()

    return redirect('/user_profile')

@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


@app.route('/reviews', methods=['POST'])
def reviews():
    global CURRENT_STORE_ID
    CURRENT_STORE_ID = request.form['store_id']
    print("CURRENT_STORE_ID = "+str(CURRENT_STORE_ID))

    return redirect('/reviews_page')

@app.route('/reviews_page')
def reviews_page():
    # get the right store_id
    global CURRENT_STORE_ID
    params = {}
    params["store_id"] = CURRENT_STORE_ID

    
    select_query = 'SELECT * from user_reviews where store_id=:store_id'
    cursor = g.conn.execute(text(select_query),params)
    record = cursor.fetchone()
    cursor.close()
    store_reviews = []
    
    s = record[2]
    input_string = s.strip('{}')
    # Split the string into individual tuples
    tuples = [tuple(x.strip('()').split(',')) for x in input_string.split(',')]
    length = len(tuples) 
    

    for i in range(0, int(length), 4):
        reviews = {}
        reviews['first_name'] = tuples[i][0].strip('("')
        reviews['last_name'] = tuples[i+1][0].strip('"(') 
        reviews['rating'] = int(tuples[i+2][0]) 
        reviews['review'] = tuples[i+3][0].strip('\\"')
        store_reviews.append(reviews)
   
    return render_template("reviews.html", store_reviews=store_reviews)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    rating = request.form['rating']
    review = request.form['review']

    global CURRENT_USER_ID
    params = {}
    params["user_id"] = CURRENT_USER_ID
    select_query = "SELECT * from users where user_id=:user_id"

    cursor = g.conn.execute(text(select_query),params)
    record = cursor.fetchone()
    first_name = record[1]
    last_name = record[2]
    cursor.close()


    # get the right store_id
    global CURRENT_STORE_ID
    params = {}
    params["store_id"] = CURRENT_STORE_ID
    params["first_name"] = first_name
    params["last_name"] = last_name
    params["rating"] = rating
    params["review"] = review
    
    select_query = "UPDATE user_reviews SET user_reviews = user_reviews || ARRAY[ROW(:first_name,:last_name,:rating,:review)::reviews] WHERE store_id=:store_id"
    g.conn.execute(text(select_query),params)
    g.conn.commit()

    return redirect('/reviews_page')
    

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using:

            python server.py

        Show the help text using:

            python server.py --help

        """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
