from twisted.internet import endpoints, protocol, reactor, threads
from twisted.protocols import basic
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall, deferLater
from dataclasses import dataclass

################
# telnet localhost 1079
#################

class BuildProtocol(basic.LineReceiver):
    def connectionMade(self):
        self.factory.client = self
        self.transport.write(b"Salut! Send start to run the builds. Send quit to exit\n")
    
    def lineReceived(self, line):    
        if line == b'quit':
            self.transport.write(b"Bye!\n")
            self.transport.loseConnection()
            return
  
        if line == b'start':
            self._handle_builds()
            return
        
    @inlineCallbacks
    def _handle_builds(self):
        yield self.factory.start_builds()
       
       
@dataclass
class Builder:
    name: str
    threshold: int     
                
class BuildFactory(protocol.ServerFactory):
    protocol = BuildProtocol

    def startFactory(self):
        self.client = None
        self.counter = 100 # Counter for host load simulation
        self.builders = [
            Builder("b1", 55),
            Builder("b2", 70),
            Builder("b3", 80)
        ]
        self.pending = set()

        # Counter loop
        self.loop = LoopingCall(self._decrement_counter)
        self.loop.start(1.0)

    def _decrement_counter(self):
        if self.counter > 50:
            self.counter -= 1
            print("Counter:", self.counter)
        else:
            print("Stopping counter loop")
            self.loop.stop()

    @inlineCallbacks
    def start_builds(self):
        for builder in self.builders:
            if builder.name not in self.pending:
                self.pending.add(builder.name)
                self._queue_single_build(builder)

    @inlineCallbacks
    def _queue_single_build(self, builder):              
        
        if self.client:
            self.client.transport.write(
                f"Requesting build: {builder.name}\n".encode()
            )   
        
        can_start = yield self.canStartBuild(builder)
        while not can_start:
            yield deferLater(reactor, 1.0, lambda: None)
            can_start = yield self.canStartBuild(builder)

        duration = yield self._start_build(builder)
        self.pending.remove(builder.name)

        if self.client:
            self.client.transport.write(
                f"Build completed: {builder.name} in {duration} seconds\n".encode()
            )

    @inlineCallbacks
    def _start_build(self, builder):
        import random
        delay = random.randint(1, 10)
        if self.client:
            self.client.transport.write(
                f"{builder.name}: started\n".encode()
            )
        yield deferLater(reactor, delay, lambda: None)
        return delay
    
    @inlineCallbacks
    def canStartBuild(self, builder):
        load = yield threads.deferToThread(self.get_load_from_api)
        if self.client:
            self.client.transport.write(
                f"{builder.name}: current load {load}, threshold {builder.threshold}\n".encode()
            )
        return load < builder.threshold
        
    def get_load_from_api(self): # Simulate blocking Zabbix call
        import time
        time.sleep(5)
        return self.counter
        

        
endpoint = endpoints.serverFromString(reactor, "tcp:1079")
endpoint.listen(BuildFactory())
reactor.run()
