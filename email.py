#!/usr/bin/python
import time, imaplib, getpass, socket

missing_libs = []

# Try to import pynotify
try:
    import pynotify
except ImportError:
    missing_libs.append('python-notify')

# Try to import gnomekeyring
try:
    import gnomekeyring as gk
except ImportError:
    missing_libs.append('python-gnomekeyring')

# Print error message and exit if a library is missing
if len(missing_libs) is not 0:
    print 'You\'re missing libraries!\napt-get install', " ".join(missing_libs)
    exit(0)   

# Which keyring and key to use to store login information
KEYRING_NAME = 'login'
KEY_NAME = 'Gmail Watcher Login'

# Clear old login entry and create a new one from user input
def new_auth():
    # Clear all old entries
    try:
        for item in gk.find_items_sync(gk.ITEM_GENERIC_SECRET, {'application': KEY_NAME}):
            gk.item_delete_sync(KEYRING_NAME, item.item_id)
    except gk.NoMatchError: pass
    
    # Read in username and password
    user = raw_input('User: ')
    passwd = getpass.getpass()
    
    # Save the user as an attribute, set application to make this easier to iterate through
    attrs = {'user': user, 'application': KEY_NAME}

    gk.item_create_sync(KEYRING_NAME, gk.ITEM_GENERIC_SECRET, KEY_NAME, attrs, passwd, True)
    
    return user,passwd

def start_session():
    try:
        return imaplib.IMAP4_SSL('imap.gmail.com','993')
    except socket.error:
        return None

def login(user,passwd):
    # Start the IMAP session with gmail
    print 'Starting SSL IMAP session, could take a minute'
    
    session = start_session()
    
    if session is None:
        print 'What is gmail? (your connection or dns may be down)'
        print 'Trying until I succeed!'
        
        while session is None:
            time.sleep(5)
            session = start_session()
                
    logged_in = False

    # Try to log in until it succeeds, try new login information if it fails
    while not logged_in:
        try:
            print 'Trying to log in...'
            session.login(user,passwd)
            print 'Successfully authenticated!'
            logged_in = True
            
        except imaplib.IMAP4.error as err:
            print 'Could not authenticate! '
            user,passwd = new_auth()
    
    return session
    
if __name__ == "__main__":
    # See if previous login information exists in the keyring
    try:
        info = gk.find_items_sync(gk.ITEM_GENERIC_SECRET, {'application': KEY_NAME})
        user = info[0].attributes['user']
        passwd = info[0].secret

    # If not, read in and store new login information
    except gk.NoMatchError:
        user,passwd = new_auth()

    session = login(user,passwd)

    # Watch emails
    print 'Watching inbox \'till (Ctrl+C) do us part'
    try:
        # Get the initial list of unread emails
        read_in = False
        
        while not read_in:
            try:
                session.select()
                prev = session.search(None,'UNSEEN')[1][0].split(' ')
                read_in = True
            except socket.error:
                print 'Disconnected! Trying to reconnect'
                session = login(user,passwd)
        
        
        # Get the initial number of unread emails
        if prev[0] is '':
            count = 0
        else:
            count = len(prev)
        
        # Display initial number of unread emails
        if count is 1:
            n = pynotify.Notification("Successfully Authenticated!", "%d unread email" % count, "gmail")
        else:
            n = pynotify.Notification("Successfully Authenticated!", "%d unread emails" % count, "gmail")
        
        n.show()
        
        while True:
            # Get a list of unread emails
            
            session.select()
            unread = session.search(None,'UNSEEN')[1][0].split(' ')
            
            # Check if any of the unread emails is new
            for email in unread:
                if email not in prev and email is not '':
                    # Display a notification if there is a new unread email
                    count = len(unread)
                    
                    if count is 1:
                        n = pynotify.Notification("New Email!", "%d unread email" % count, "gmail")
                    else:
                        n = pynotify.Notification("New Email!", "%d unread emails" % count, "gmail")
                    
                    n.show()
                    break;
            
            prev = unread
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print 'Logging out'
        session.logout()

