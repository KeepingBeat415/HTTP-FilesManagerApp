## Run Router for simulate UDP protocol packet delayed and drop

- Default router IP: localhost, PORT: 3000
- Max delay: 3000ms (limit by UDP waiting timeout)

### Router Setting

- ./router -port=3000 --drop-rate=0.5 --max-delay=0ms --seed=1 (drop rate only)
- ./router -port=3000 --drop-rate=0 --max-delay=1000ms --seed=1 (delayed only)
- ./router -port=3000 --drop-rate=0.3 --max-delay=1000ms --seed=1 (both drop and delay)

## The cURL-like command line

- Default Server IP: localhost, PORT: 8007
- Default Support PORT Number: 2. For example: (8007, 8008)

### HTTP GET

- httpc get -v -h Accept:application/xml 'http://localhost:8007/' (GET file list)
- httpc get -v -h Accept:application/json 'http://localhost:8007/foo' (GET 'foo' file content)

### HTTP POST

- httpc post -v -h Content-Type:application/json -d '{"File Path": "data/foo","Course": "COMP445","Assignment": 3}' http://localhost:8007/foo (inline parameter POST)

### Multi-client Connection with PORT: 8007, 8008

- httpc get -v -h Accept:text/plain 'http://localhost:8007/foo'
- httpc post -v -h Content-Type:application/json -d '{"File Path": "data/foo","Course": "COMP445","Assignment": 3}' http://localhost:8007/foo

- httpc get -v -h Accept:text/plain 'http://localhost:8008/foo'
- httpc post -v -h Content-Type:application/json -d '{"File Path": "data/foo","Course": "COMP445","Assignment": 3}' http://localhost:8008/foo
