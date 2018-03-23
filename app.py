######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for, session
from flaskext.mysql import MySQL
import flask.ext.login as flask_login
import datetime
from collections import OrderedDict

#for image uploading
from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'Tony'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'zgrmws137' #CHANGE THIS TO YOUR MYSQL PASSWORD
app.config['MYSQL_DATABASE_DB'] = 'photo_share_project'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
# all users' email
users = cursor.fetchall()


def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

def getFriendsList(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT U.email, U.first_name, U.last_name from Users U, user_friend UF WHERE UF.friend_id = U.user_id and UF.user_id = '{0}'".format(uid))
	return cursor.fetchall()

def getNonFriendsList(uid):
	cursor = conn.cursor()
	cursor.execute("select U.email, U.first_name, U.last_name from Users U where U.user_id not in (select uf.friend_id from user_friend uf where uf.user_id = '{0}') and U.user_id <> '{0}' and U.user_id <> 1".format(uid))
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''
# TODO need to make login page beautiful
@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return render_template('login.html')


	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email

			# Tony ADD
			session['logged_in'] = True

			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	# TODO need to make it beautiful
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	# set is_logged_in
	session['logged_in'] = False
	# back to homepage
	return flask.redirect(flask.url_for('hello'))

@login_manager.unauthorized_handler
def unauthorized_handler():

	return render_template('hello.html', is_logged_in=False, is_unauth=True)

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register/", methods=['GET'])
def register():
	return render_template('improved_register.html', supress='True')

@app.route("/register/", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		birth = request.form.get('birthday')
		first_name = request.form.get('firstname')
		last_name = request.form.get('lastname')
		hometown = request.form.get('hometown')
		gender = request.form.get('gender')
		print(email)
		print(birth)
		print(first_name)
		print(last_name)
		print(hometown)
		print(gender)
		password=request.form.get('password')
	except:
		print("couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, birth, first_name, last_name, gender, hometown, password) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, birth, first_name, last_name, gender, hometown, password)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=getUserNameFromEmail(flask_login.current_user.id), message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

# TODO

def getPhotoFromPhotoID(photo_id):
	cursor = conn.cursor()
	cursor.execute(
		"select P.imgdata, P.photo_id, P.caption, P.likes from Photos P where P.photo_id = '{0}'".format(
			photo_id))
	return cursor.fetchall()

def getTagsUsingUIDForRecomendations(user_id):
	cursor = conn.cursor()
	cursor.execute("select H.word, count(*) from (select T.word from Photos P, photo_associate_tag PAT, Tags T where P.user_id = '{0}' and P.photo_id = PAT.photo_id and PAT.tag_id = T.tag_id) as H group by H.word order by count(*) desc limit 5".format(user_id))
	return cursor.fetchall()

def checkIfCanDeletePhotoUsingPhotoIDAndUserID(photo_id, user_id):
	cursor = conn.cursor()
	cursor.execute("select * from Photos where user_id = '{0}' and photo_id = '{1}'".format(user_id, photo_id))
	return cursor.fetchall()

def getPhotosFromSearchingTags(tags):
	cursor = conn.cursor()
	cursor.execute(
		"select P.photo_id from Photos P, Tags T, photo_associate_tag PAT where P.photo_id = PAT.photo_id and PAT.tag_id = T.tag_id and T.word = '{0}'".format(
			tags))
	return cursor.fetchall()

def getPhotosFromUserLikes(uid):
	cursor = conn.cursor()
	cursor.execute(
		"select P.imgdata, P.photo_id, P.caption, P.likes from user_like_photo ULP, Photos P where ULP.photo_id = P.photo_id and ULP.user_id = '{0}'".format(
			uid))
	return cursor.fetchall()

def checkIfIsLiked(user_id, photo_id):
	cursor = conn.cursor()
	cursor.execute("select * from user_like_photo where user_id = '{0}' and photo_id = '{1}'".format(user_id, photo_id))
	return cursor.fetchall()

def getTop10Tags():
	cursor = conn.cursor()
	cursor.execute("select distinct T.word from Tags T GROUP BY T.tag_id ORDER BY (select count(T2.word) from Tags T2 where T.word = T2.word) DESC limit 10")
	return cursor.fetchall()

def getTop10CommentedPhotos():
	cursor = conn.cursor()
	cursor.execute(
		"SELECT P.imgdata, P.photo_id, P.caption, U.user_id, P.likes from Photos P, Users U, Comments C, photo_to_comment PTC where U.user_id = P.user_id and P.photo_id = PTC.photo_id and PTC.comment_id = C.comment_id GROUP by P.photo_id ORDER by (select count(PTC2.comment_id) from photo_to_comment PTC2 where PTC2.photo_id = P.photo_id) desc limit 10"
	)
	return cursor.fetchall()

def getTop10LikedPhotos():
	cursor = conn.cursor()
	cursor.execute(
		"SELECT P.imgdata, P.photo_id, P.caption, P.user_id, P.likes from Photos P GROUP by P.photo_id  ORDER by P.likes desc limit 10"
	)
	return cursor.fetchall()

def getTop10Contributions():
	cursor = conn.cursor()
	cursor.execute("select email, first_name, last_name, contributions, user_id from Users where user_id <> 1 GROUP by user_id ORDER by contributions DESC LIMIT 10")
	return cursor.fetchall()

def getPhotoTagsFromPhotoId(photo_id):
	cursor = conn.cursor()
	cursor.execute("select T.word from Tags T, photo_associate_tag AST where T.tag_id = AST.tag_id and AST.photo_id = '{0}'".format(photo_id))
	return cursor.fetchall()

def getPhotosByTag(tag):
	cursor = conn.cursor()
	cursor.execute(
		"select P.imgdata, P.photo_id, P.caption, P.likes from Tags T, photo_associate_tag AST, Photos P where AST.photo_id = P.photo_id and T.tag_id = AST.tag_id and T.word = '{0}'".format(
			tag))
	return cursor.fetchall()

def getPhotoCommentsFromPhotoId(photo_id):
	cursor = conn.cursor()
	cursor.execute("select C.comment_text, C.comment_date, U.first_name, U.last_name from Users U, photo_to_comment PTC, Comments C where C.user_id = U.user_id and PTC.photo_id = '{0}' and PTC.comment_id = C.comment_id".format(photo_id))
	return cursor.fetchall()

def getPhotoInfoFromPhotoId(photo_id):
	cursor = conn.cursor()
	cursor.execute("select P.imgdata, P.caption, U.first_name, U.last_name, A.name from Albums A, Photos P, album_contain_photo ACP, Users U where P.photo_id = '{0}' and ACP.photo_id = '{0}' and P.user_id = U.user_id and ACP.album_id = A.album_id".format(photo_id))
	return cursor.fetchone()


def getUserIDFromPhotoID(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Photos WHERE photo_id = '{0}'".format(photo_id))
	return cursor.fetchone()[0]

def getPhotosFromAlbumUsingAlbumId(album_id):
	cursor = conn.cursor()
	cursor.execute("select P.imgdata, P.photo_id, P.caption, P.likes from album_contain_photo ACP, Photos P where ACP.photo_id = P.photo_id and ACP.album_id = '{0}'".format(album_id))
	return cursor.fetchall()

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute(
		"SELECT imgdata, photo_id, caption, likes FROM Photos WHERE user_id = '{0}'".format(uid)
	)
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getAllPhotos():
	cursor = conn.cursor()
	cursor.execute(
		"SELECT P.imgdata, P.photo_id, P.caption, P.likes, U.user_id from Photos P, Users U WHERE P.user_id = U.user_id"
	)
	return cursor.fetchall()

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def getUserNameFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT first_name, last_name FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()

def getUserNameFromID(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT first_name, last_name FROM Users WHERE user_id = '{0}'".format(uid))
	return cursor.fetchone()

def getUserAlbum(uid):
	cursor = conn.cursor()
	cursor.execute("select name, album_date, image, album_id from Albums where user_id = '{0}'".format(uid))
	return cursor.fetchall()

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code



@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=getUserNameFromEmail(flask_login.current_user.id), photos=getUsersPhotos(getUserIdFromEmail(flask_login.current_user.id)), message="Here's your profile", is_logged_in=True, can_delete=True)

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		# TODO need to fix
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album_id = request.form.get('album_id')
		print(album_id)


		tags = list()
		const = 1
		const_str = str(const)
		tag = request.form.get(const_str)
		while tag != None:
			tags.append(tag)
			const = const + 1
			const_str = str(const)
			tag = request.form.get(const_str)




		photo_data = base64.standard_b64encode(imgfile.read()).decode('utf-8')

		cursor = conn.cursor()
		cursor.execute("INSERT INTO Photos (user_id, imgdata, caption) VALUES ('{0}', '{1}', '{2}' )".format(uid, photo_data, caption))
		cursor.execute("insert into album_contain_photo (album_id, photo_id) values ('{0}', (select MAX(photo_id) from Photos))".format(album_id))
		cursor.execute("UPDATE Users SET contributions=contributions + 1 WHERE user_id='{0}'".format(uid))
		# insert tags!
		for tag in tags:
			cursor.execute("INSERT INTO Tags (word) VALUES ('{0}')".format(tag))
			cursor.execute("insert into photo_associate_tag (tag_id, photo_id) values ((select MAX(tag_id) from Tags),(select MAX(photo_id) from Photos))")


		conn.commit()
		return render_template('hello.html', name=getUserNameFromEmail(flask_login.current_user.id),
							   photos=getUsersPhotos(getUserIdFromEmail(flask_login.current_user.id)),
							   message="Photouploaded!", is_logged_in=True)


	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return  render_template('hello.html', is_logged_in=True, message='Upload a photo!', upload=True, albums_info=getUserAlbum(uid))
		# return render_template('upload.html')
#end photo uploading code 


@app.route("/photo_detail", methods=['POST'])
def photo_detail():
	if request.method == 'POST':


		photo_id = request.form.get('photo_id')
		photo_detail_info = getPhotoInfoFromPhotoId(photo_id)
		photo_detail_tags = getPhotoTagsFromPhotoId(photo_id)
		user_first_last_name = list()


		if request.form.get('comment'):
			comment = request.form.get('comment')
			cursor = conn.cursor()
			comment_date = datetime.datetime.now().strftime('%Y-%m-%d')
			if flask_login.current_user.is_authenticated:
				user_id = getUserIdFromEmail(flask_login.current_user.id)

				# check: user cannot leave comment to their own photos
				print(user_id)
				print(getUserIDFromPhotoID(photo_id))
				if user_id == getUserIDFromPhotoID(photo_id):
					return render_template('hello.html', message="Sorry you can't add comment to your own photo", is_logged_in=True )
				cursor.execute("UPDATE Users SET contributions=contributions + 1 WHERE user_id='{0}'".format(user_id))
				cursor.execute("insert into Comments (comment_text, user_id, comment_date) values ('{0}', (select U.user_id from Users U, Photos P where U.user_id = '{3}' and P.photo_id = '{1}'), '{2}')".format(comment, photo_id, comment_date, user_id))
				cursor.execute("insert into photo_to_comment (comment_id, photo_id) values ((select MAX(comment_id) from Comments), '{0}')".format(photo_id))
				conn.commit()
				photo_detail_comments = getPhotoCommentsFromPhotoId(photo_id)
				return render_template('hello.html', is_logged_in=True, photo_detail=True, photo_detail_info=photo_detail_info, photo_detail_tags=photo_detail_tags, photo_detail_comments=photo_detail_comments, photo_id=photo_id)
			else:
				cursor.execute(
					"insert into Comments (comment_text, user_id, comment_date) values ('{0}', 1, '{1}')".format(
						comment, comment_date))
				cursor.execute(
					"insert into photo_to_comment (comment_id, photo_id) values ((select MAX(comment_id) from Comments), '{0}')".format(
						photo_id))
				conn.commit()
				photo_detail_comments = getPhotoCommentsFromPhotoId(photo_id)
			return render_template('hello.html', is_logged_in=False, photo_detail=True,
								   photo_detail_info=photo_detail_info, photo_detail_tags=photo_detail_tags,
								   photo_detail_comments=photo_detail_comments, photo_id=photo_id)


		else:
			# TODO
			photo_detail_comments = getPhotoCommentsFromPhotoId(photo_id)
			if flask_login.current_user.is_authenticated:
				return render_template('hello.html', is_logged_in=True, photo_detail=True, photo_detail_info=photo_detail_info, photo_detail_tags=photo_detail_tags, photo_detail_comments=photo_detail_comments, photo_id=photo_id)
			else:
				return render_template('hello.html', is_logged_in=False, photo_detail=True, photo_detail_info=photo_detail_info, photo_detail_tags=photo_detail_tags, photo_detail_comments=photo_detail_comments, photo_id=photo_id)




#friend list
@app.route("/friends", methods=['GET', 'POST'])
@flask_login.login_required
def friends():
	nonFriend = getNonFriendsList(getUserIdFromEmail(flask_login.current_user.id))
	if request.method == 'GET':
		return render_template('hello.html', is_logged_in=True, name=getUserNameFromEmail(flask_login.current_user.id), myfriends=getFriendsList(getUserIdFromEmail(flask_login.current_user.id)), nonfriends=nonFriend)
	else:
		user_id = getUserIdFromEmail(flask_login.current_user.id)
		# TODO
		friend_email = request.form.get("friend_email")
		friend_id = getUserIdFromEmail(friend_email)
		print(user_id)
		print(friend_id)
		cursor = conn.cursor()
		cursor.execute("INSERT INTO user_friend (user_id, friend_id) VALUES ('{0}', '{1}')".format(user_id, friend_id))
		conn.commit()
		return flask.redirect(flask.url_for('friends'))

@app.route("/album", methods=['GET', 'POST'])
@flask_login.login_required
def album():
	if request.method == 'POST':
		detail = request.form.get('detail')
		if detail:
			return render_template('hello.html', is_logged_in=True, message='Here is your photos in your album' ,photos=getPhotosFromAlbumUsingAlbumId(detail))
		else:
			uid = getUserIdFromEmail(flask_login.current_user.id)
			imgfile = request.files['photo']
			title = request.form.get('title')
			album_date = datetime.datetime.now().strftime('%Y-%m-%d')
			photo_data = base64.standard_b64encode(imgfile.read()).decode('utf-8')
			cursor = conn.cursor()
			# cursor.execute("insert into user_own_album (user_id, album_id) values ('{0}', '{1}')".format(uid, album_id))
			cursor.execute("INSERT INTO Albums (name, album_date, user_id, image) VALUES ('{0}', '{1}', '{2}', '{3}' )".format(title, album_date, uid, photo_data))
			conn.commit()
			return render_template('hello.html', is_logged_in=True, albums = getUserAlbum(getUserIdFromEmail(flask_login.current_user.id)), is_album=True)
	else:
		return render_template('hello.html', is_logged_in=True, albums = getUserAlbum(getUserIdFromEmail(flask_login.current_user.id)), is_album=True)


@app.route("/explore/view_by_tags", methods=['POST'])
def view_by_tags():
	if request.method == 'POST':
		tag_info = request.form.get('tag_info')
		tag = "#"+ tag_info
		if not session.get('logged_in'):
			return render_template('hello.html', is_logged_in=False, photos=getPhotosByTag(tag_info), message=tag)
		else:
			return render_template('hello.html', is_logged_in=True, photos=getPhotosByTag(tag_info), message=tag)


@app.route("/explore/top10_contributions", methods=['GET'])
def explore():
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, contributions=getTop10Contributions(), message="The Top10 Make Contributions Users")
	else:
		return render_template('hello.html', is_logged_in=True, contributions=getTop10Contributions(),  message="The Top10 Make Contributions Users")


@app.route("/explore/top10_commented", methods=['GET'])
def top10_commented():
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, photos=getTop10CommentedPhotos(),
							   message="The Top10 Commented Photos")
	else:
		return render_template('hello.html', is_logged_in=True, photos=getTop10CommentedPhotos(),
							   message="The Top10 Commented Photos")


@app.route("/explore/top10_tags", methods=['GET'])
def top10_tags():
	toptags = getTop10Tags()
	print(toptags)
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, toptags=toptags,
							   message="The Top10 Tags")
	else:
		return render_template('hello.html', is_logged_in=True, toptags=toptags,
							   message="The Top10 Tags")
# @app.route("/explore", methods=['GET'])
# def explore():


@app.route("/likes", methods=['GET','POST'])
@flask_login.login_required
def likes():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':

		photo_id = request.form.get('photo_id')
		cursor = conn.cursor()
		is_liked = checkIfIsLiked(user_id, photo_id)
		if is_liked != ():
			return render_template('hello.html', is_logged_in=True, photos=getAllPhotos(), message="You already liked this photo!")
		else:
			cursor.execute("UPDATE Photos SET likes=likes + 1 WHERE photo_id='{0}'".format(photo_id))
			cursor.execute("insert into user_like_photo (user_id, photo_id) values ('{0}', '{1}')".format(user_id, photo_id))
			conn.commit()
			return flask.redirect(flask.url_for('hello'))
	else:
		return render_template('hello.html', is_logged_in=True, photos=getPhotosFromUserLikes(user_id),
							   message="Here is the photos you liked!")


@app.route("/search", methods=['POST'])
def search():
	tags_from_user = request.form.get('search')
	tag_str = str(tags_from_user)
	tag_str2 = "#" + tag_str
	tags = tag_str.split()
	final_list = list()

	if tags == "":
		if not session.get('logged_in'):
			return render_template('hello.html', is_logged_in=False, message="please put tags")
		else:
			return render_template('hello.html', is_logged_in=True, message="please put tags")

	cursor = conn.cursor()
	for tag in tags:
		print(tag)
		cursor.execute("select PAT.photo_id from photo_associate_tag PAT, Tags T where T.tag_id = PAT.tag_id and T.word = '{0}'".format(tag))
		s = cursor.fetchall()
		lst = list()
		for i in range(len(s)):
			t = s[i][0]
			lst.append(t)

		if final_list == []:
			final_list.append(lst)
		else:
			ret_list = [item for item in final_list if item not in lst]
			print(ret_list)
			final_list = ret_list

	if final_list[0] == []:
		if not session.get('logged_in'):
			return render_template('hello.html', is_logged_in=False, message="tags not exist")
		else:
			return render_template('hello.html', is_logged_in=True, message="tags not exist")

	photoID = final_list[0]

	query = "select imgdata, photo_id, caption, likes from Photos where "
	for id in photoID:
		query += "photo_id = " + str(id) + " or "
	query = query[:-4]
	query += ";"
	cursor.execute(query)
	pho = cursor.fetchall()
	conn.commit()
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, photos=pho, message=tag_str2)
	else:
		return render_template('hello.html', is_logged_in=True, photos=pho, message=tag_str2)


@app.route("/delete_photo", methods=['POST'])
@flask_login.login_required
def delete_photo():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	photo_id = request.form.get('photo_id')
	can_delete = checkIfCanDeletePhotoUsingPhotoIDAndUserID(photo_id, user_id)
	if can_delete != ():
		cursor = conn.cursor()
		cursor.execute("DELETE FROM Photos WHERE photo_id='{0}'".format(photo_id))
		conn.commit()
		return flask.redirect(url_for('protected'))
	else:
		return render_template('hello.html', is_logged_in=True, message="Sorry you don't have the access to delete the photo!")

@app.route("/delete_album", methods=['POST'])
@flask_login.login_required
def delete_album():
	album_id = request.form.get('album_id')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Albums WHERE album_id='{0}'".format(album_id))
	conn.commit()
	return flask.redirect(url_for('album'))

@app.route("/recommendations", methods=['GET'])
@flask_login.login_required
def recommendations():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	tags = getTagsUsingUIDForRecomendations(user_id)

	diction = dict()
	for tag in tags:
		photo_id = getPhotosFromSearchingTags(tag[0])
		for p_id in photo_id:

			if p_id[0] in diction:
				diction[p_id[0]] += 1
			else:
				diction[p_id[0]] = 1
	s = [(k, diction[k]) for k in sorted(diction, key=diction.get, reverse=True)]

	photos = list()
	for i in range(len(s)):
		print(s[i][0])
		photos.append(getPhotoFromPhotoID(s[i][0])[0])
	return render_template('hello.html', name=getUserNameFromEmail(flask_login.current_user.id), photos=photos, message="We recommend you:", is_logged_in=True)


@app.route("/top10_liked", methods=['GET'])
def top10_liked():
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, photos=getTop10LikedPhotos(), message="Here is the Top 10 liked photos")
	else:
		return render_template('hello.html', is_logged_in=True, photos=getTop10LikedPhotos(), message="Here is the Top 10 liked photos")

#default page
@app.route("/", methods=['GET'])
def hello():
	if not session.get('logged_in'):
		return render_template('hello.html', is_logged_in=False, photos=getAllPhotos())
	else:
		return render_template('hello.html', is_logged_in=True, photos=getAllPhotos())

	# return render_template('hello.html', message='Welcome', )
	# is_logged_in=False


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
