#!/usr/bin/env python
#-*- coding:utf-8 -#-
import subprocess
from socket import inet_aton
import socket
import re
from re import match
from os import path,geteuid,makedirs
from datetime import datetime


TextColorRed='\x1b[31m'
TextColorGreen='\x1b[32m'
TextColorWhite='\x1b[0m'

def checkRootPrivilege():
###  检查脚本的当前运行用户是否是 ROOT ###
  RootUID=subprocess.Popen(['id','-u','root'],stdout=subprocess.PIPE).communicate()[0]
  RootUID=RootUID.strip()
  CurrentUID=geteuid()
  return str(RootUID)==str(CurrentUID)


def extractLocalIP():
    return subprocess.Popen("ip addr|grep 'state UP' -A2|tail -n1|awk '{print $2}'|cut -f 1 -d '/'",
                            shell=True,stdout=subprocess.PIPE).communicate()[0].strip()

def checkPortState(host='127.0.0.1',port=9200):
### 检查对应服务器上面的port 是否处于TCP监听状态 ##

    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(1)
    try:
       s.connect((host,port))
       return {'RetCode':0,
               'Result':TextColorGreen+str(host)+':'+str(port)+'处于监听状态'+TextColorWhite}
    except:
       return {'RetCode':1,
               'Result':TextColorRed+'无法访问'+str(host)+':'+str(port)+TextColorWhite}


def isIPValid(ip):
    if not isinstance(ip,str) and not isinstance(ip,unicode):
        return False
    ## 检查IP 地址是否有效###
    ip=ip.strip()
    if len(ip.split('.'))==4:
        try:
            inet_aton(ip)
            tmpList=filter(lambda x:match(r'^[^0]+',x) or match(r'^0$',x),ip.split('.'))
            if len(tmpList)!=4:
                return False
            return True
        except:
            return False
    return False



def setupConsul():
    if path.isfile(path.join('/TRS','APP','Consul')):
        print (TextColorRed+'无法创建/TRS/APP/Consul 文件夹,程序退出'+TextColorWhite)
        exit(1)

    if not path.isdir(path.join('/TRS','APP','Consul')):
        print ('创建/TRS/APP/consul 目录')
        makedirs(path.join('/TRS','APP','Consul'))

    if not path.isdir(path.join('/TRS','APP','Consul','data')):
        print ('创建/TRS/APP/Consul/data 目录')
        makedirs(path.join('/TRS','APP','Consul','data'))
    if not path.isdir(path.join('/TRS','APP','Consul','backup')):
        print ('创建/TRS/APP/Consul/backup 目录')
        makedirs(path.join('/TRS','APP','Consul','backup'))
    if not path.isdir(path.join('/TRS','APP','Consul','conf.d')):
        print ('创建/TRS/APP/Consul/conf.d 目录')
        makedirs(path.join('/TRS','APP','Consul','conf.d'))


    TmpLocalIP=extractLocalIP()
    TmpLocalIP=TmpLocalIP.strip()
    if not isIPValid(TmpLocalIP):
        print (TextColorRed+'无法获取本地IP地址，程序退出'+TextColorWhite)
        exit(1)

    subprocess.call('firewall-cmd --zone=public --add-port=8300/tcp --permanent',shell=True)
    subprocess.call('firewall-cmd --zone=public --add-port=8600/tcp --permanent',shell=True)
    subprocess.call('firewall-cmd --zone=public --add-port=8600/udp --permanent',shell=True)
    subprocess.call('firewall-cmd --zone=public --add-port=8500/tcp --permanent',shell=True)
    subprocess.call('firewall-cmd --reload',shell=True)

    with open(r'consul.service',mode='r') as f:
        TmpFileContent=f.read()

    TmpFileContent=TmpFileContent%(TmpLocalIP,TmpLocalIP)
    with open(r'/etc/init.d/consul',mode='w') as f:
        f.write(TmpFileContent)
    subprocess.call('chmod 777 /etc/init.d/consul',shell=True)
    subprocess.call('systemctl daemon-reload',shell=True)

    if not path.isfile(r'/TRS/APP/Consul/consul'):
        subprocess.call('cp consul /TRS/APP/Consul',shell=True)
    with open(r'/etc/profile',mode='r') as f:
        TmpFileContent=f.read()

    if  '/TRS/APP/Consul' not in TmpFileContent:
        TmpFileContent=TmpFileContent+'\n'+'export PATH=${PATH}:/TRS/APP/Consul'
    with open('/etc/profile',mode='w') as f:
        f.write(TmpFileContent)
    subprocess.call('source /etc/profile',shell=True)

def exportKV():
    if subprocess.call('/TRS/APP/Consul/consul members',shell=True):
        print (TextColorRed+'检测到本地未安装Consul，或者consul未启动，无法备份，程序退出'+TextColorWhite)
        exit(1)
    if not path.isdir(r'/TRS/APP/Consul/backup'):
        if path.isfile(r'/TRS/APP/Consul/backup'):
            print (TextColorRed+'无法创建/TRS/APP/Consul/backup 文件夹,备份失败，程序退出'+TextColorWhite)
            exit(1)
        makedirs(path.join('/TRS','APP','Consul','backup'))

    TmpCurrentTimeString=datetime.now().strftime('%Y-%m-%d__%H-%M-%S')
    BackupFilePath='/TRS/APP/Consul/backup/'+'consul_backup_'+str(TmpCurrentTimeString)
    if subprocess.call('/TRS/APP/Consul/consul kv export >%s'%(BackupFilePath,),shell=True):
        print (TextColorRed+'备份失败.'+TextColorWhite)
        return 1
    print (TextColorGreen+'备份成功，备份文件存放路径：'+BackupFilePath+TextColorWhite)


def importKV():
    while True:
        print ("重要提示：")
        print ('    您正在对Consul备份数据进行恢复操作，这将导致之前所有数据被覆盖!')
        choice=raw_input('是否继续(yes/no):')
        choice=choice.strip().lower()

        if choice=='yes':
            break
        elif choice=='no':
            return 1
    TmpFileName=raw_input('请输入需还原的文件名称：')
    TmpFileName=TmpFileName.strip()
    if not path.isfile(r'/TRS/APP/Consul/backup/'+TmpFileName):
        print (TextColorRed+'无法找到/TRS/APP/Consul/backup/'+TmpFileName+' 备份文件，无法还原，程序退出'+TextColorWhite)
        exit(1)
    if subprocess.call('/TRS/APP/Consul/consul members',shell=True):
        print (TextColorRed+'检测到本地未安装Consul，或者consul未启动，无法还原，程序退出'+TextColorWhite)
        exit(1)

    TmpFilePath='/TRS/APP/Consul/backup/'+TmpFileName
    if  subprocess.call('/TRS/APP/Consul/consul kv import @%s'%(TmpFilePath,),shell=True):
        print (TextColorRed+'还原失败，程序退出.'+TextColorWhite)
        exit(1)
    print (TextColorGreen+'备份文件还原成功'+TextColorWhite)





if __name__=='__main__':
    if not checkRootPrivilege():
        print (TextColorRed+'需要ROOT 账号运行本工具，当前用户不满足，程序退出.'+TextColorWhite)
        exit(1)
    while True:
        print (TextColorGreen+'#########  欢迎使用“海云系统”，本工具将帮助你完成Consul相关操作。  ######')
        print ('           1、安装 Consul;')
        print ('           2、备份 Consul K/V;')
        print ('           3、恢复 Consul K/V;')
        print ('           0、退出安装;'+TextColorWhite)

        choice=raw_input('请输入数值序号:')
        choice=choice.strip()

        if choice=='1':
            setupConsul()
            continue
        elif choice=='2':
            exportKV()
            continue
        elif choice=='3':
            importKV()
            continue
        elif choice=='0':
            break