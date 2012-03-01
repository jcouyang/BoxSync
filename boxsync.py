#!/usr/bin/python
#coding:utf-8
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import boxdotnet
import os
import ConfigParser
import pickle
import atexit
from string import maketrans
API_KEY=''
AUTH_TOKEN=''
BOX_FOLDER='/TEST'
SYNC_FOLDER=''
SHARE = ''
CONFIG=None
BOX=None
ACDATA=None
#中文ok
class BoxError(Exception):
    """Exception class for errors received from Facebook."""
    pass

class SyncEventHandler(FileSystemEventHandler):
    
    def on_created(self, event):
        scr=event.src_path.decode('utf-8')
        super(SyncEventHandler, self).on_created(event)
        cwd = event.src_path.replace(SYNC_FOLDER,'')
        box_cwd=BOX_FOLDER+cwd
        what = 'directory' if event.is_directory else 'file'
        logging.info("Creating %s: %s", what, cwd)
        
        if event.is_directory:
            rs=BOX.create_folder(
                name=os.path.basename(event.src_path),
                parent_id=ACDATA[os.path.split(box_cwd)[0]]['id'],
                share=SHARE,
                api_key=API_KEY,
                auth_token=AUTH_TOKEN)
            status = rs.status[0].elementText
            if status =='create_ok':
                ACDATA[box_cwd]={}
                ACDATA[box_cwd]['id']=rs.folder[0].folder_id[0]
                ACDATA[box_cwd]['parent']=rs.folder[0].parent_folder_id[0]
                
                logging.info("created Dir %s to %s", event.src_path,box_cwd)
            else:
                logging.warning(status)
        elif  os.path.basename(cwd)[0]!='.':
            # print type(event.src_path),event.src_path
            rs=BOX.upload(
                filename=event.src_path,
                folder_id=ACDATA[os.path.split(box_cwd)[0]]['id'],
                share=SHARE,
                api_key=API_KEY,
                auth_token=AUTH_TOKEN)
            status = rs.status[0].elementText
            if status =='upload_ok':
                logging.info("uploaded %s to %s", event.src_path, box_cwd)
            else:
                
                logging.warning(status)
       
def _updata(xml,id,data,prefix):  
    for item in xml:
        parent=prefix
        if item.elementName=='folder':
            data[prefix+item['name']]={}
            data[prefix+item['name']]['id']=item['id']
            data[prefix+item['name']]['parent']=id
            parent=''.join([prefix,item['name']])+'/'
            try:
                _updata(item.folders[0].folder,item['id'],data,parent)
            except:
                pass
    return data

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)
    CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)
    c=CONFIG.read('config.cfg')
    if len(c)==0:
        CONFIG.add_section('UserSetting')
        CONFIG.set('UserSetting','sync_path','~/BoxSync')
        CONFIG.set('UserSetting','box_path','/TEST')
        CONFIG.set('UserSetting','auth_token')
        CONFIG.set('UserSetting','share','0')
        with open('config.cfg', 'wb') as configfile:
            CONFIG.write(configfile)
        CONFIG.read('config.cfg')
    SYNC_FOLDER= CONFIG.get('UserSetting','sync_path')
    SYNC_FOLDER = os.path.expanduser(SYNC_FOLDER)
    BOX_FOLDER = CONFIG.get('UserSetting','box_path')
    SHARE =  CONFIG.get('UserSetting','share')


    #---------FULL SYNC ------------------
    BOX= boxdotnet.BoxDotNet()

    try:
        data_file = open('data.p','rb')
        ACDATA=pickle.load(data_file)
        logging.info('load data')
        
    except:
        actree = BOX.get_account_tree(api_key=API_KEY,auth_token=AUTH_TOKEN,folder_id=0,params=['nozip','simple'])
        logging.info(actree.status[0].elementText)
        ACDATA = _updata(actree.tree[0].folder[0].folders[0].folder,'0',{},'/')
        print ACDATA
        with open('data.p','wb') as data_file:
            pickle.dump(ACDATA,data_file)

    
    event_handler = SyncEventHandler()
    
    observer = Observer()
    observer.schedule(event_handler, path=SYNC_FOLDER, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print 'Saving'
        with open('data.p','wb') as data_file:
            pickle.dump(ACDATA,data_file)
        data_file.close()
        print 'bye!'
        observer.stop()
    observer.join()
