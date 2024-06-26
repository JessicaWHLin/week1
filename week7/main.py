from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import mysql.connector
from pydantic import BaseModel
import re
from urllib.parse import quote

mydb = mysql.connector.connect(
  host="localhost",
  user="test2",
  password="1234",
  database="website"
  )
mycursor = mydb.cursor()


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(SessionMiddleware, secret_key="myscret_")

def verify(request: Request, username: str, password: str):
        sql_verify="select id, name, username from member where username= %s and password=%s"
        val_verify=(username,password)
        mycursor.execute(sql_verify,val_verify)
        result_verify=mycursor.fetchone() 
        if result_verify:
                user_id, user_name,user_username = result_verify
                request.session["user_id"]=user_id
                request.session["user_name"]=user_name
                request.session["user_username"]=user_username
                return True
        else:
                return False

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
        return templates.TemplateResponse(
            request=request, name="index.html")

@app.post("/signup", response_class=RedirectResponse)
async def signup(request:Request, iniName : str=Form(...), iniUsername: str=Form(...), iniPassword: str=Form(...)):
        sql_check="SELECT * FROM member WHERE username = %s"
        val_check=(iniUsername,) 
        mycursor.execute(sql_check,val_check)
        check_result=mycursor.fetchone()
        #後端檢查密碼限制
        #拿到輸入的密碼→檢查規則→若符合規則:進行註冊；若不符合規則:redriect或傳回error給前端
        rules= r'^[a-zA-Z0-9@#$%]{4,8}$'
        if(re.match(rules,iniPassword)!=None):
                if check_result == None:
                        sql_add="insert into member(name,username,password)values( %s,%s,%s )"
                        val_add=(iniName,iniUsername,iniPassword)
                        mycursor.execute(sql_add,val_add)
                        mydb.commit()
                        mycursor.close()
                        return RedirectResponse(url="/",status_code=303)
                else:
                        return RedirectResponse(url="/error?message=重複帳號", status_code=303)
        else:
                encoded_message=quote("密碼需4~8碼含英文及數字及@#$%")
                return RedirectResponse(url=f"/error?message={encoded_message}",status_code=303)
                
@app.post("/signin" , response_class=RedirectResponse)
async def signin(request: Request, username : str=Form(None), password: str= Form(None)):
        veri=verify(request,username,password)
        if veri==True :
                return RedirectResponse(url="/member", status_code=303)
        else:
                return RedirectResponse(url="/error?message=帳號，或密碼錯誤", status_code=303)

@app.get("/error",response_class=HTMLResponse)
async def error(request: Request,message: str):
        return templates.TemplateResponse("error.html", {"request":request, "message": message})

@app.get("/member", response_class=HTMLResponse)
async def member(request: Request):
        if request.session.get("user_id")!=None:
                current_name=request.session.get("user_name")
                current_id=request.session.get("user_id")
                sql_query="select member.name,member.id,content,message.id from message join member on message.member_id=member.id order by message.id desc"
                mycursor.execute(sql_query)
                messages=mycursor.fetchall()
                meg=[{"name":x,"id":y,"message":z,"meg_id":i} for x,y,z,i in messages]  
                return templates.TemplateResponse("member.html",{"request":request, "current_name":current_name,"messages":meg,"current_id":current_id})
        else:
                return RedirectResponse(url="/", status_code=303)        

@app.post("/createMessage", response_class=RedirectResponse)
async def create_message(request:Request, message :str=Form(None)):
       if request.session.get("user_id")!=None:
                user_id=request.session.get("user_id")
                sql_insert="insert into message(member_id,content)values(%s,%s)"
                val_insert=(user_id,message)
                mycursor.execute(sql_insert,val_insert)
                mydb.commit()
                # mycursor.close()
                return RedirectResponse(url="/member",status_code=303)
       else:
               return RedirectResponse(url="/", status_code=303)
               
class Item(BaseModel):
       meg_id:int

@app.post("/deleteMessage", response_class=RedirectResponse)
async def delete_message(request:Request, item: Item):
       if request.session.get("user_id")!=None:
                meg_id=item.meg_id
                sql_query="select member_id from message where id=%s"
                val_query=(meg_id,)
                mycursor.execute(sql_query,val_query)
                member_id=mycursor.fetchone()
                if member_id[0]==request.session.get("user_id"):
                        sql_delete="delete from message where id=%s"
                        val_delete=(meg_id,)
                        mycursor.execute(sql_delete,val_delete)
                        mydb.commit()
                        # mycursor.close()
                        return RedirectResponse(url="/member",status_code=303)
                else:
                        return RedirectResponse(url="/", status_code=303)
       else:
               return RedirectResponse(url="/", status_code=303)       
       
@app.get("/signout",response_class=RedirectResponse)
async def signout(request: Request):    
        request.session["user_id"]=None
        request.session["user_name"]=None
        request.session["user_username"]=None
        return RedirectResponse(url="/member", status_code=303)

@app.get("/api/member",response_class=JSONResponse)
async def query_name(request:Request, username:str):
        if request.session.get("user_id")!= None :
                sql_query="select id, name, username from member where username=%s"
                val_query=(username,)
                mycursor.execute(sql_query,val_query)
                results=mycursor.fetchone()
                if results != None:
                        data={"id":results[0],"name":results[1],"username":results[2] } 
                        return {"data":data}   
        else:
                data=None
                return {"data":data}
        
class item2(BaseModel):
        name:str

@app.patch("/api/member",response_class=JSONResponse)
async def update_name(request:Request, item:item2):
        if request.session.get("user_id")!= None :
                sql_update="update member set name=%s where id=%s"
                val_update=(item.name,request.session.get("user_id"))
                mycursor.execute(sql_update,val_update)
                mycursor.fetchone()
                mydb.commit()
                # mycursor.close()
                request.session["user_name"]=item.name
                result={"ok":True}
                return {"data":result}
        else:
                result={"error":True}
                return {"data":result}
          