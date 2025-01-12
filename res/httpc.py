import re, sys, os.path, time, logging, socket, ipaddress
from urllib.parse import urlparse
from const import *
from udpService import udpService

class Httpc():

    def __init__(self):
        self.is_verbose = False
        self.is_download = False
        self.passed_headers = ""
        self.file_name = ""
        self.body = ""
        self.redirect_times = 0
        self.method = ""

    # Execute cURL commend line
    def execute_curl(self, cmd):
        print(BREAK_LINE)
        if("help" in cmd and "get" in cmd):
            self.get_help_info("get")
        elif("help" in cmd and "post" in cmd):
            self.get_help_info("post")
        elif("help" in cmd):
            self.get_help_info("none")
        elif("-d" in cmd and "-f" in cmd):
            print("\n[ERROR]: Invalid Command, POST should have either -d or -f but not both.")
        # HTTP Request
        elif(cmd.startswith("httpc get") or cmd.startswith("httpc post")):
            self.reset_param()
            self.http_request(cmd)
        else:
            print("\n[ERROR]: Invalid Command.")

    # Parse HTTP Request
    def http_request(self, cmd):
        # -v enables a verbose output which display response header and body
        if ("-v" in cmd): self.is_verbose = True
        
        # Display logging debug msg
        if(self.is_verbose):
            logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', stream=sys.stdout, level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', stream=sys.stdout, level=logging.INFO)

        # -o download response body into file
        if ("-o" in cmd): 
            if(re.search(r'-o (\S.+?\S+)', cmd)):
                self.file_name = (re.findall(r'-o (\S.+?\S+)', cmd))[0]
                self.is_download = True
            else:
                self.handle_exception("The download file name NOT exist.")
        # -f get file name for to associate the body of the HTTP POST
        if ("-f" in cmd): 
            if(re.search(r'-f (\S.+?\S+)', cmd)):
                self.file_name = (re.findall(r'-f (\S.+?\S+)', cmd))[0]
            else:
                self.handle_exception("The file name NOT exist")
        # -h pass headers to HTTP GET
        if ("-h" in cmd): self.passed_headers =  self.get_passed_headers_value(cmd)
        # -d associate the body of the HTTP POST with the inline data
        if ("-d" in cmd or "-f" in cmd): self.body = self.get_passed_body_value(cmd)
        # Extract URL
        if(re.search(r'(https?://.+?\S+)', cmd)):
            url = (re.findall(r'(https?://.+?\S+)', cmd))[0] if ("post" in cmd) else (re.findall(r'\'(https?://.*)\'', cmd))[0]
        else:
            self.handle_exception("The URL is Invalid.")

        # print("[DEBUG]: Parsed URL -> ", urlparse(url))
        # Format HTTP Header and Body
        if(cmd.startswith("httpc get")): 
            self.method = "GET"
            self.get_request(urlparse(url))
        if(cmd.startswith("httpc post")): 
            self.method = "POST"
            self.post_request(urlparse(url))

    # Format GET Request
    def get_request(self, url):
        path_with_query = url.path
        if(url.query): path_with_query += '?' + url.query

        header = ( 
            "GET " + path_with_query + " HTTP/1.0\r\n" +
            "Host: " + url.hostname + "\r\n" +
            "User-Agent: Concordia-HTTP/1.0\r\n" +
            self.passed_headers + "\r\n" +
            "\r\n")
        self.socket_service(url, header)

    # Format POST Request
    def post_request(self, url):
        header = (
            "POST " + url.path + " HTTP/1.0\r\n" +
            "Host: " + url.hostname + "\r\n" +
            "User-Agent: Concordia-HTTP/1.0\r\n" +
            self.passed_headers + "\r\n" +
            "Content-Length: " + str(len(self.body)) + "\r\n" +
            "\r\n"
        )
        self.socket_service(url, header + self.body)

    # Socket Service
    def socket_service(self, url_parsed, request):

        # Initialize Client Socket
        client_udp_socket = udpService()
        # Convert localhost to 127.0.0.1
        peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(url_parsed.hostname))

        try:
            # Connect UDP Socket
            client_udp_socket.connect_server(peer_ip_addr, url_parsed.port)
            # Sent HTTP Request
            client_udp_socket.send_data(request.encode("utf-8"))
            # Store HTTP Response
            response = client_udp_socket.received_data()

            # Parse HTTP Response
            response_parsed = HttpResponseParsed(response.decode("utf-8"))
            # -f then Download Response Body
            if(self.is_download): self.download_response(response_parsed)
            # Display HTTP Response
            self.print_response(response_parsed)
            # Redirect into another URL
            if(response_parsed.code in REDIRECT_CODE):
                # Format URL, for example: https://google.ca/
                if self.redirect_times < 6:
                    url = url_parsed.scheme + "://" + url_parsed.hostname + response_parsed.location[0]
                    logging.info("HTTP Client -- Redirect To New Location: ", url)
                    # GET or POST redirect call
                    if(self.method == "GET"):
                        self.get_request(urlparse(url))
                    else:
                        self.post_request(urlparse(url))
                    self.redirect_times += 1
                else:
                    self.redirect_times = 0
                    return self.handle_exception("Redirected 5 times, no more redirect allowed.")                   
        except:
            self.handle_exception("The ERROR Exists when connect with SERER SOCKET.")
        finally:
            client_udp_socket.close()

    # Get headers
    def get_passed_headers_value(self, cmd):
        # For example: -h key1:value1 -h key2:value2
        if(re.search(r'-h (\S+:\S+)', cmd)):
            headers = re.findall(r'-h (\S+:\S+)', cmd)
        else:
            self.handle_exception("The GET headers is Invalid.")
        logging.info(f"HTTP Client -- Accept Headers values: {headers}")
        return "\r\n".join(headers)

    # POST body
    def get_passed_body_value(self, cmd):
        bodies = ""
        if ("-d" in cmd):
            # For example: -d '{"Course": "COMP445","Assignment": 1}'
            bodies = re.findall(r'\'(.+?)\'', cmd)[0] if (re.search(r'\'(.+?)\'', cmd))  else self.handle_exception("The POST bodies is Invalid.")
            logging.info(f"HTTP Client -- POST Body Value from inline: {bodies}")
        if ("-f" in cmd):
            # Check whether file exist, then read content
            if (os.path.exists("data/"+self.file_name)):
                with open("data/"+self.file_name) as file:
                    bodies = file.read().replace('\n', '')
                    logging.info(f"HTTP Client -- POST Body Value from file: {bodies}")
            else:
                self.handle_exception("The File NOT Exited.")
        return bodies

    # Download Response into File
    def download_response(self, response):

        logging.debug(f"HTTP Client -- Download Response Body into {self.file_name}")
        # Create new file if not exist, otherwise overwrite
        file = open("data/"+self.file_name, "w") if (os.path.exists("data/"+self.file_name)) else open("data/"+self.file_name, "a")

        for line in response.body: file.write(line)

        file.close()

    def handle_exception(self, msg):

        logging.info(f"\nHTTP Client -- ERROR: {msg}")
        # Handle exception with ask new input commend line
        try:
            cmd = input("\n  Enter commands line begin with \"httpc\". \n  Type help to list commands.\n  Press 'Ctrl+C' or Type 'quit' to terminate.\n\n")
            if("quit" in cmd): sys.exit()
            self.execute_curl(cmd)
        except KeyboardInterrupt:
            sys.exit()

    def print_response(self, response):
        if(self.is_verbose):
            print("\n[DEBUG]: === Received Response Header. === \n")
            for line in response.headers: print(line)
        print("\n[DEBUG]: === Received Response Body. === \n")
        for line in response.body: print(line)

    # Reset Parameter for each comment line
    def reset_param(self):
        self.is_verbose = False
        self.is_download = False
        self.passed_headers = ""
        self.file_name = ""
        self.body = ""
        self.method = ""
        
    # Display Help Information
    def get_help_info(self, arg):
        if(arg == "post"):
            print('\nusage: httpc post [-v] [-h key:value] [-d inline-data] [-f file] URL\n' +
            'Post executes a HTTP POST request for a given URL with inline data or from file.\n' +
            '  -v Prints the detail of the response such as protocol, status, and headers.\n' +
            '  -h key:value Associates headers to HTTP Request with the format \'key:value\'.\n' +
            '  -d string Associates an inline data to the body HTTP POST request.\n' +
            '  -f file Associates the content of a file to the body HTTP POST request\n' +
            'Either [-d] or [-f] can be used but not both.\n')
        elif(arg == "get"):
            print('\nusage: httpc get [-v] [-h key:value] URL\n' +
            'Get executes a HTTP GET request for a given URL.\n' +
            '  -v Prints the detail of the response such as protocol, status, and headers.\n' +
            '  -h key:value Associates headers to HTTP Request with the format \'key:value\'.\n')
        else:
            print('\nhttpc is a curl-like application but supports HTTP protocol only.\n' +
            'Usage: \n' + 
            '  httpc command [arguments]\n' + 
            'The commands are: \n' + 
            '  get executes a HTTP GET request and prints the response.\n' +
            '  post executes a HTTP POST request and prints the resonse.\n' +
            '  help prints this screen.\n')

class HttpResponseParsed():

  def __init__(self, response):
    self.parseText(response)

  def parseText(self, response):
    
    # print("[DEBUG]: Received Raw Data -> ", response)
    contents = response.split("\r\n\r\n")

    self.headers = contents[0].split("\r\n")
    self.body = contents[1].split("\r\n")
    self.code = self.headers[0].split(" ")[1]
    self.status = " ".join(self.headers[0].split(" ")[2:])
    self.location = ""
    
    logging.info(f"HTTP Client -- Received Response Code: {self.code}, Received Response Statue: {self.status}")

    if(self.code in REDIRECT_CODE):
        for header in self.headers:
            if("location" in header): self.location = re.findall(r'(\S+/\S+)', header)

print("\n"+"="*10+"Welcome to HTTPC Service"+"="*10)

# Initial HTTP 
httpc = Httpc()
#Program Start
# while True: 
#     try:
#         cmd = input("\n Enter commands line begin with \"httpc\". \n  Type help to list commands.\n  Press 'Ctrl+C' or Type 'quit' to terminate.\n\n")
#         if("quit" in cmd): break
#         httpc.execute_curl(cmd)
#     except KeyboardInterrupt:
#         sys.exit()


# ============ AUTO DEBUG For A3 ============
input_cmd_A3 = [
"httpc get -v 'http://localhost:8007/'",

"httpc get -v -h Accept:text/plain 'http://localhost:8007/foo'",
"httpc post -v -h Content-Type:text/plain -f foo http://localhost:8007/foo",

"httpc post -v -h Content-Type:application/json -d '{\"File Path\": \"data/foo\",\"Course\": \"COMP445\",\"Assignment\": 3}' http://localhost:8007/foo",

"httpc get -v -h Accept:text/plain 'http://localhost:8007/sample'",
"httpc post -v -h Content-Type:text/plain -f sample http://localhost:8007/sample",
]

for cmd in input_cmd_A3:
    print("\ncmd -> "+cmd+"\n")
    httpc.execute_curl(cmd)
    time.sleep(2)