import os, logging, sys, json, re, threading, time

class FileManager():

    thread_lock = threading.Lock()

    def __init__(self, verbose, dir_path, request):

        # Display logging debug msg
        if(verbose):
            logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', stream=sys.stdout, level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', stream=sys.stdout, level=logging.INFO)

        self.dir_path = os.path.dirname(os.path.realpath(__file__)) + "/" + dir_path
        self.status = { "200":"OK", "400":"Bad Request", "401":"Unauthorized", "404":"Not Found"}
        
        self.code = ""
        self.response_content = ""

        self.disposition = ""
        self.response_dic = {}
        self.accept_type = "json"
 
        self.parse_data(request)


    def parse_data(self, request):

        header, body = request.split("\r\n\r\n")
        headers = header.split("\r\n")

        #logging.debug(f"Received Processing Request: Header -> {header}, Body -> {body}")

        method, src_path, self.http_version = headers[0].split(" ")
        # Request with Accept type
        if(re.search(r'Accept:(.+?\S+)', header)):
            accept_type = re.findall(r'Accept:\s*(.+?\S+)', header)[0]
            self.accept_type = self.process_accept_type(accept_type)

        logging.debug(f"FileManager -- Method: {method}, Path: {src_path}, Version: {self.http_version}, AcceptType: {self.accept_type}")

        # Process HTTP request with header
        dic = {}
        for header in headers[1:]:
            key, value = header.split(":")
            dic[key] = value
        self.response_dic["headers"] = dic

        if(method == "GET"):
            self.handle_GET_file_request(src_path)

        if(method == "POST"):
            self.response_dic["data"] = body
            self.handle_POST_file_request(src_path)
    
    def handle_GET_file_request(self, src_path):
        # Process GET request with inline parameters, For example /get?course=networking&assignment=2
        if (re.search(r'/get\?(\S+)', src_path)):
            dic = {}
            params = re.findall(r'/get\?(\S+)', src_path)[0]
            for param in params.split("&"):
                key, value = param.split("=")
                dic[key] = value
            self.response_dic["arg"] = dic

            self.code = "200"
            self.response_content = json.dumps(self.response_dic, indent=2, sort_keys=True)
        # General GET files list request as "/", and GET file content
        elif(src_path == "/"):
            self.get_files_list()
        else:
            self.get_file_content(src_path)
        
        logging.debug(f"FileManager -- Processed GET response: Code => {self.code}, Body => {self.response_dic}")
    
    # Call File Manager
    def handle_POST_file_request(self, src_path):

        if(src_path == "/post"):
            self.code = "200"
            self.response_dic = json.dumps(self.response_dic, indent=2, sort_keys=True)
        else:
            self.post_file_handler(src_path, self.response_dic["data"])

            # With 200 code as successes, and ERROR with 401, 404
            if(self.code == "200"):
                self.response_content = json.dumps(self.response_dic, indent=2, sort_keys=True)

        logging.debug(f"FileManager -- Processed POST response: Code => {self.code}, Body => {self.response_dic}")
    

    def get_files_list(self):
        # Support only HTML/XML/TXT/JSON
        if (self.accept_type == "NONE"):
            self.code = "400"
            return self.html_exception_handler(self.code, self.status.get("400"), "Accept file type not supported.")

        files_list = []
        self.code = "200"
        # Read all file name in the directory
        for (self.dir_path, dir_names, file_names) in os.walk(self.dir_path):
            files_list.extend(file_names)

        content = " | ".join(files_list)
    
        self.generate_file_by_type(self.accept_type, content)

    
    def generate_file_by_type(self, accept_type, content):

        if(accept_type == "json"):
            self.response_content = json.dumps({"data":content}, indent=2, sort_keys=True) 
        elif(accept_type == "txt"):
            self.response_content = content
        elif(accept_type == "xml"):
            self.generate_xml_file(content)
        else:
            self.generate_html_file(content)

    # Process only handle Four different type 
    def process_accept_type(self, accept_type):
        dic_type = {"application/json":"json", "application/xml":"xml", "text/html":"html", "text/plain":"txt"}
        # if not exist, then set as NONE
        return dic_type.get(accept_type, "NONE")


    def get_file_content(self, path):

        # Handle Content-Disposition 
        if("/download" in path):
            file_name = re.findall(r'/(.+?)/', path)[0]
            logging.debug(f"File Name => {file_name}")
            path = "/" + file_name
            self.disposition = f"Content-Disposition: attachment; filename=\"{file_name}.{self.accept_type}\"\r\n"

        dir_path = self.dir_path + path

        # Handle use ".." to access parent directory
        if("../" in dir_path):
            self.code = "401"
            logging.info(f"FileManager -- Attempt get content from path: {path}, cause 401 - \"Unauthorized\"")
            self.html_exception_handler(self.code, self.status.get("401"), "Attempt access unauthorized file.")
        # Handle file not exists
        elif(not os.path.exists(dir_path)):
            self.code = "404"
            logging.info(f"FileManager -- Attempt get content from path: {path}, cause 404 - \"Not Found\"")
            self.html_exception_handler(self.code, self.status.get("404"), "Access file not exist.")
        else:
            self.code = "200"
            
            self.thread_lock.acquire()
            logging.debug(f"FileManager -- GET Thread Lock is Active, with path: {path}")

            with open(dir_path) as file:
                content = file.read()
                logging.debug(f"FileManager -- POST Body Value from File -> {content}") 
            
            #self.thread_lock_hold("GET", 5)

            self.thread_lock.release()
            logging.debug(f"FileManager -- GET Thread Lock is Release, with path: {path}")

            logging.info(f"FileManager -- Attempt get content from path: {path}, cause 200 - \"OK\"")

            self.generate_file_by_type(self.accept_type, content)


    def post_file_handler(self, path, content):

        dir_path = self.dir_path + path

        # Handle use ".." to access parent directory
        if("../" in dir_path):
            self.code = "401"
            logging.info(f"FileManager -- Attempt post content to path: {path}, cause 401 - \"Unauthorized\"")
            self.html_exception_handler(self.code, self.status.get("401"), "Attempt access unauthorized file.")

        # Handle file not exists
        elif(not os.path.exists(dir_path)):
            self.code = "404"
            logging.info(f"FileManager -- Attempt post content to path: {path}, cause 404 - \"Not Found\"")
            self.html_exception_handler(self.code, self.status.get("404"), "Access file not exist.")
        else:
            self.code = "200"

            self.thread_lock.acquire()
            logging.debug(f"FileManager -- POST Thread Lock is Active, with path {path}")

            with open(dir_path, "w") as file:
                file.write(content)
            file.close()

            #self.thread_lock_hold("POST", 5)

            self.thread_lock.release()
            logging.debug(f"FileManager -- POST Thread Lock is Release, with path {path}. POST content: {content}")

            logging.info(f"FileManager -- Attempt post content to path: {path}, cause 200 - \"OK\"")

    def html_exception_handler(self, code, status, msg):
        logging.debug(f"FileManager -- Exception handler: Code => {code}, Status => {status}, Msg => {msg}")

        self.response_content =  (
                        "<html>\n"+
                        f"  <head><title>{code} {status}</title></head>\n"+
                        "  <body>\n"
                        f"    <center><h1>{code} -- {status}</h1></center>\n"
                        f"    <center><h1>{msg}</h1></center>\n"
                        "  </body>\n"
                        "</html>\n")


    def generate_xml_file(self, content):
        self.response_content = (
                "<note>\n"+
                "  <heading> XML File </heading>\n"+
                f"  <body>{content}</body>\n"+
                "</note>\n")


    def generate_html_file(self, content):
        self.response_content =  (
                "<html>\n"+
                "  <head><title>HTML File</title></head>\n"+
                "  <body>\n"
                f"    <center><h1>{content}</h1></center>\n"
                "  </body>\n"
                "</html>\n")


    def thread_lock_hold(self, msg, count):
        while count:
            time.sleep(5)
            print(f"\n[DEBUG]: {msg} Thread Lock -- "+"%s -- Countdown: %s" % (time.ctime(time.time()), count))
            count -= 1