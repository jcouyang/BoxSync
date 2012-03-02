#!/usr/bin/python
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
class BoxError(Exception):
    """Exception class for errors received from Facebook."""
    pass

class SyncEventHandler(FileSystemEventHandler):

    def on_moved(self, event):
        global ACDATA
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        super(SyncEventHandler, self).on_moved(event)
        cwd = event.src_path.replace(SYNC_FOLDER,'')
        box_cwd=BOX_FOLDER+cwd
        dest= event.dest_path.replace(SYNC_FOLDER,'')
        box_dest=BOX_FOLDER+dest
        parent,base = os.path.split(box_dest)
        if ACDATA.has_key(box_cwd):
            on_created(self,event)
        what = 'directory' if event.is_directory else 'file'
        target='folder' if event.is_directory else 'file'
        if os.path.split(event.src_path)[0]==os.path.split(event.dest_path)[0]:
            # rename
            
            logging.info("Renaming %s %s to %s", what, cwd,dest)
            rs = BOX.rename(
                target=target,
                target_id=ACDATA[box_cwd]['id'],
                new_name=base,
                api_key=API_KEY,
                auth_token=AUTH_TOKEN)
            status = rs.status[0].elementText
            if status =='s_rename_node':
                ACDATA[box_dest]=ACDATA.pop(box_cwd)
                logging.info("Renamed Dir %s to %s",box_cwd,box_dest)
            else:
                logging.warning(status)
        else:
            # move
           
            logging.info("Moving %s %s to %s", what, cwd,dest)

           
            rs=BOX.move(
                target=target,
                target_id=ACDATA[box_cwd]['id'],
                destination_id=ACDATA[parent],
                api_key=API_KEY,
                auth_token=AUTH_TOKEN)
            status = rs.status[0].elementText
            if status =='s_move_node':
                ACDATA[box_dest]=ACDATA.pop(box_cwd)

                logging.info("Moved Dir %s to %s",box_cwd,box_dest)
            else:
                logging.warning(status)
        if target=='folder':
            actree = BOX.get_account_tree(api_key=API_KEY,auth_token=AUTH_TOKEN,folder_id=0,params=['nozip','simple'])
            logging.info(actree.status[0].elementText)
            ACDATA = _updata(actree.tree[0].folder[0].folders[0].folder,'0',{},'/')
        
    def on_deleted(self, event):
        """Called when a file or directory is deleted.
        :param event: Event representing file/directory deletion.
        :type event: :class:`DirDeletedEvent` or :class:`FileDeletedEvent` """
        
    def on_modified(self, event):
        """Called when a file or directory is modified.
        :param event: Event representing file/directory modification.
        :type event: :class:`DirModifiedEvent` or :class:`FileModifiedEvent` """

        
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
                _updata(item.files[0].file,item['id'],data,parent)
            except:
                pass
        if item.elementName=='file':
            data[prefix+item['file_name']]={}
            data[prefix+item['file_name']]['id']=item['id']
            data[prefix+item['file_name']]['parent']=id
            data[prefix+item['file_name']]['updated']=item['updated']
            data[prefix+item['file_name']]['share']=item['shared']
            data[prefix+item['file_name']]['sha1']=item['sha1']
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
    API_KEY = CONFIG.get('UserSetting','api_key')
    AUTH_TOKEN=CONFIG.get('UserSetting','auth_token')
    SHARE =  CONFIG.get('UserSetting','share')


   
    BOX= boxdotnet.BoxDotNet()
    
    # try:
    #     data_file = open('data.p','rb')
    #     ACDATA=pickle.load(data_file)
    #     logging.info('load data')
        
    # except:
        
    #     actree = BOX.get_account_tree(api_key=API_KEY,auth_token=AUTH_TOKEN,folder_id=0,params=['nozip','simple'])
    #     logging.info(actree.status[0].elementText)
    #     ACDATA = _updata(actree.tree[0].folder[0].folders[0].folder,'0',{},'/')
    #     print ACDATA
    #     with open('data.p','wb') as data_file:
    #         pickle.dump(ACDATA,data_file)
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
             #---------FULL SYNC ------------------ every five min
            
            time.sleep(1)
    except KeyboardInterrupt:
        print 'Saving'
        with open('data.p','wb') as data_file:
            pickle.dump(ACDATA,data_file)
            print 'Saved'
        data_file.close()
        print 'Bye!'
        observer.stop()
    observer.join()
