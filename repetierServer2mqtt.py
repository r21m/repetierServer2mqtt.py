import configparser
import json
import paho.mqtt.client as mqtt
import time
import urllib.request
import logging

class load_config():
    def __init__(self,conf_file = 'config.conf'):
        self.conf_file = conf_file
        self.config = configparser.ConfigParser()
        self.config.read(self.conf_file)
        self.sections = self.config.sections()
        self.config_dict = {}
        self.get_config()

    def get_config(self):
        tmp_dict = {}
        for section in self.sections:
            option = self.config.options(section)
            for key in option:
                val = self.set_type(self.config[section][key])
                tmp_dict[key] = (val)
            self.config_dict[section] = tmp_dict
            tmp_dict = {}
        return self.config_dict

    def set_type(self,data):
        try:
           if (".") in data: data = (float(data))
           else: data = (int(data))
        except ValueError:
            data = (str(data))
            if data == '': data = None
        return data

class repetier():
    def __init__(self,rep_serv,port,api_key,https = False,debug = True):
        self.rep_serv = rep_serv
        self.port = port
        self.api_key = api_key
        self.debug = debug
        self.printer_names = None

        self.state_list = {}
        self.printer_data = {}
   
        if not https: self.http = ('http')
        else: self.http = ('https')

        if self.api_key == ('auto'):
            try:
                info = self.get_info()
                self.api_key = info['apikey']
            except KeyError:
                print('Unable to get automatic api key')
                exit()
            
        self.server_name = self.get_server_name()
        
    def get_state_list(self):
        state_list_msg = self.rq_url('stateList')
        self.state_list = self.get(state_list_msg)
        #self.debug_msg(self.state_list)
        return self.state_list
    
    def get_list_printer(self):
        printer_data_msg = self.rq_url('listPrinter') #listPrinter
        self.printer_data = self.get(printer_data_msg)
        #self.debug_msg(self.printer_data)
        return self.printer_data
    
    def get_messages(self):
        printer_data_msg = self.rq_url('messages')
        self.printer_data = self.get(printer_data_msg)
        #self.debug_msg(self.printer_data)
        return self.printer_data

    def ping(self):
        printer_data_msg = self.rq_url('ping')
        self.printer_data = self.get(printer_data_msg)
        #self.debug_msg(self.printer_data)
        return self.printer_data

    def get_response(self,msg):
        printer_data_msg = self.rq_url(msg)
        self.printer_data = self.get(printer_data_msg)
        #self.debug_msg(self.printer_data)
        return self.printer_data

    def get_info(self):
        info = '/printer/info'
        printer_info_msg = ('%s://%s:%s%s' %(self.http,
                                             self.rep_serv,
                                             self.port,
                                             info))
        self.printer_info = self.get(printer_info_msg)
        #self.debug_msg(self.printer_info)
        return self.printer_info

    def get_server_name(self):
        info = self.get_info()
        self.server_name = info['servername']
        return self.server_name

    def rq_url(self,insert):
        _insert = insert
        ret_url = ('%s://%s:%s/printer/api/?a=%s&data=&apikey=%s' %(self.http,
                                                                    self.rep_serv,
                                                                    self.port,
                                                                    _insert,
                                                                    self.api_key))
        return ret_url

    def get(self,msg):
        #print(msg)
        try:
            response = urllib.request.urlopen(msg)
            response = response.read()
            json_data = json.loads(response)
            #json_data = json.dumps(json_data)
            return json_data
        except ConnectionResetError:
            return {'except':'ConnectionResetError'}
        except urllib.error.URLError:
            return {'error':'urllib.error.URLError'}
        except TimeoutError:
            return {'error':'TimeoutError'}
        #except urllib.request.timeout:
        #    return {'error':'socket.timeout'}
    
    def debug_msg(self,msg):
        if self.debug:
            print(msg)

class mqtt_client():
    def __init__(self,broker_ip,
                 broker_port,topic ,
                 qos = 0,
                 keepalive = 6,
                 debug = True,
                 auto_connect = False,
                 client_id= ''):
        self.client_id = client_id
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.topic = topic
        self.qos = qos
        self.keepalive = keepalive
        self.client = mqtt.Client()
        self.debug = debug
        self.connect_state = None
        if auto_connect:
            self.connect()

    def connect(self):
        try:
            self.client.connect(self.broker_ip,
                                self.broker_port,
                                self.keepalive)
            self.connect_state = True
        except ConnectionRefusedError:
            print('MQTTConnectionRefusedError')
            self.connect_state = False
            return False
        
    def disconnect(self):
        self.client.disconnect()
        return
    
    def publish(self,topic_add = '',msg = None,retain = False):
        _topic = ('/%s/%s' %(self.topic,topic_add))
        #self.debug_msg(msg)
        #print(msg)
        #print(_topic,msg)
        self.client.publish(topic = _topic,
                            payload = msg,
                            qos=self.qos,
                            retain=retain)
        return
    
    def debug_msg(self,msg):
        if self.debug:
            print(msg)

        
load_config = load_config()
conf_dict = load_config.get_config()

mqtt_client = mqtt_client(conf_dict['MQTT']['broker'],
                          conf_dict['MQTT']['broker_port'],
                          conf_dict['MQTT']['topic'],
                          debug = False,
                          auto_connect = True)

repetier = repetier(conf_dict['REPETIER']['server'],
                    conf_dict['REPETIER']['port'],
                    conf_dict['REPETIER']['api_key']
                    ,debug = False)

cyc = 0

while True:
    print(cyc)
    if mqtt_client.connect_state:
        topic_add = ('%s/%s'%(repetier.server_name,'info'))
        payload = json.dumps(repetier.get_info())
        mqtt_client.publish(topic_add,payload)
        
        topic_add = ('%s/%s'%(repetier.server_name,'state_list'))
        payload = json.dumps(repetier.get_state_list())
        mqtt_client.publish(topic_add,payload,retain = True)
        
        topic_add = ('%s/%s'%(repetier.server_name,'list_printer'))
        payload = json.dumps(repetier.get_list_printer())
        mqtt_client.publish(topic_add,payload,retain = True)
        
    else:
        mqtt_client.connect()
    cyc += 1    
    time.sleep(1)
        

    




