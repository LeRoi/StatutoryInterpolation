import requests, urllib2

def getTitles():
    r = requests.request(method='get', url='http://127.0.0.1:5000/getTitles')
    print r, r.text

def getTitle():
    title = raw_input('Title: ')
    r = requests.request(method='get', url='http://127.0.0.1:5000/getTitle',\
                     data='{"title": %s}' % title)
    print r, r.text

def getDiffs():
    r = requests.request(method='get', url='http://127.0.0.1:5000/getDiffs',\
                     data='{"title": 12}')
    print r, r.text

methods = ['getTitles', 'getTitle', 'getDiffs']
method_name_to_method = {'getTitles' : getTitles,
                         'getTitle' : getTitle,
                         'getDiffs' : getDiffs}

def print_methods():
    for m in range(len(methods)):
        print "%d: %s" % (m, methods[m])

if __name__ == '__main__':
    while True:
        print_methods()
        action = raw_input('Selection: ')
        valid = True
        try:
            action = int(action)
        except:
            valid = False
            
        if valid and action < len(methods):
            method_name_to_method[methods[action]]()
        else:
            print 'Invalid selection'
        
