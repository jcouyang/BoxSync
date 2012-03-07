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
import sys
from string import maketrans
API_KEY='ro7mkd0yge1d2ah6gupyet80cal7cyop'#BoxSyncClient
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

    moddict={}
    
    def on_deleted(self, event):
        """Called when a file or directory is deleted.
        :param event: Event representing file/directory deletion.
        :type event: :class:`DirDeletedEvent` or :class:`FileDeletedEvent` """
        logging.debug('---------DELETING or RENAMING FILE-%s----------',event.src_path)
        global ACDATA
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        super(SyncEventHandler, self).on_deleted(event)
        cwd = event.src_path.replace(SYNC_FOLDER,'')
        box_cwd=BOX_FOLDER+cwd
        if os.path.basename(box_cwd)[0]=='.':
            return
        what = 'directory' if event.is_directory else 'file'
        target='folder' if event.is_directory else 'file'
        logging.info("Deleting %s %s", what, cwd)
        try:
            rs = BOX.delete(
            target=target,
            target_id=ACDATA[box_cwd]['id'],
            api_key=API_KEY,
            auth_token=AUTH_TOKEN)
            status = rs.status[0].elementText
            if status =='s_delete_node':
                ACDATA.pop(box_cwd)
                logging.info("Deleted %s",box_cwd)
            else:
                logging.warning(status)
        except KeyError:
            print KeyError
            
    def on_modified(self, event):
        """Called when a file or directory is modified.
        :param event: Event representing file/directory modification.
        :type event: :class:`DirModifiedEvent` or :class:`FileModifiedEvent` """
        super(SyncEventHandler, self).on_modified(event)
        cwd = event.src_path.replace(SYNC_FOLDER,'')
        what = 'directory' if event.is_directory else 'file'
        
        
        if not event.is_directory:
            logging.debug("Modifying %s %s", what, cwd)
            
            #compare file mod time
            
        
    def on_created(self, event):
        global ACDATA
        
        scr=event.src_path.decode('utf-8')
        super(SyncEventHandler, self).on_created(event)
        cwd = event.src_path.replace(SYNC_FOLDER,'')
        box_cwd=BOX_FOLDER+cwd
        what = 'directory' if event.is_directory else 'file'
        
        try:
            if event.is_directory:
                logging.info("Uploading %s: %s", what, cwd)
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
                logging.info("Uploading %s: %s", what, cwd)
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
        except KeyError:
            print KeyError.args
        
        
    def on_moved(self, event):
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """
        try:
            
            global ACDATA

            super(SyncEventHandler, self).on_moved(event)
            cwd = event.src_path.replace(SYNC_FOLDER,'')
            box_cwd=BOX_FOLDER+cwd
            dest= event.dest_path.replace(SYNC_FOLDER,'')
            box_dest=BOX_FOLDER+dest
            parent,base = os.path.split(box_dest)

            if os.path.basename(box_cwd)[0]=='.' or not ACDATA.has_key(os.path.split(box_dest)[0]):
                return
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
                    destination_id=ACDATA[parent]['id'],
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
        except KeyError,e:
            print e
            
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
            try:
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
    
    CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)
    c=CONFIG.read('config.cfg')
    if len(c)==0:
        CONFIG.add_section('UserSetting')
        CONFIG.set('UserSetting','sync_path','~/BoxSync')
        CONFIG.set('UserSetting','box_path','/TEST')
        CONFIG.set('UserSetting','log',logging.INFO)
        CONFIG.set('UserSetting','auth_token')
        CONFIG.set('UserSetting','share','0')
        with open('config.cfg', 'wb') as configfile:
            CONFIG.write(configfile)
        CONFIG.read('config.cfg')
    SYNC_FOLDER= CONFIG.get('UserSetting','sync_path')
    SYNC_FOLDER = os.path.expanduser(SYNC_FOLDER)
    BOX_FOLDER = CONFIG.get('UserSetting','box_path')
    AUTH_TOKEN=CONFIG.get('UserSetting','auth_token')
    SHARE =  CONFIG.get('UserSetting','share')
    BOX= boxdotnet.BoxDotNet()
    logging.basicConfig(level=int(CONFIG.get('UserSetting','log')))
    logging.debug(AUTH_TOKEN)
    if AUTH_TOKEN is None:
        ticket = BOX.login(API_KEY)
        logging.debug('ticket2='+ticket)
        print 'Login to Auth BoxSyn App from the Page Just Popup.'
        while True:
            done_auth = raw_input('Did you finish?[Y/n]')
            if done_auth=='y' or done_auth=='':
                print 'Login sucessfully! Now you can Sync your files in folder=>'+SYNC_FOLDER
                rsp = BOX.get_auth_token(api_key=API_KEY, ticket=ticket)
                if rsp.status[0].elementText=='get_auth_token_ok':
                    AUTH_TOKEN = rsp.auth_token[0].elementText
                    CONFIG.set('UserSetting','auth_token',AUTH_TOKEN)
                    with open('config.cfg', 'wb') as configfile:
                        CONFIG.write(configfile)
                    break
                else:
                    logging.warning(rsp.status[0].elementText)
                    continue

            elif done_auth=='n':
                print 'Bye then~'
                sys.exit(0)
            else:
                print r'input only "y" or "n" or just press Enter plz.'
                
    
    
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
    actree = BOX.get_account_tree(api_key=API_KEY,auth_token=AUTH_TOKEN,folder_id=0,params=['simple'])
    logging.info(actree.status[0].elementText)
    print actree.tree[0].elementName
    ACDATA = _updata(actree.tree,'0',{},'')
    logging.debug(ACDATA)
    with open('.data.p','wb') as data_file:
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
        with open('.data.p','wb') as data_file:
            pickle.dump(ACDATA,data_file)
            print 'Saved'
        data_file.close()
        print 'Bye!'
        observer.stop()

    except KeyError:
        logging.warning(KeyError)
    observer.join()
