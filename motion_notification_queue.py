import appdaemon.plugins.hass.hassapi as hass
from collections import deque

class MotionNotificationQueue(hass.Hass):
  
  def initialize(self):
    self.queue = deque([])
    self.dependentQueues = {}

    self.motion_dict = {}
    # Find all Motionsensors
    for k,v in self.args["speakers"].items():
      self.dependentQueues[k] = deque([])
      for ms in v["motion_sensors"]:
        speaker = self.motion_dict.setdefault(ms,[]).append(k)

    #Register event to add new messages to the queues
    self.listen_event(self.AppendMessage, "message_queue")

    for ms in self.motion_dict:
      #listen to all necessary motion detectors
      self.listen_state(self.motion, ms, new = "on")
      self.log("Listen to " + ms)

  def AppendMessage(self, event_name, data, kwargs):
    self.log(data)
    if "speaker" in data:
      self.dependentQueues[data["speaker"]].append(data["message"])
      self.log("Message added to dependentQueues") 
    else:
      self.queue.append(data["message"])
      self.log("Message added to queue") 

  def motion(self, entity, attribute, old, new, kwargs):
    self.log("Motion detected")

    dependentMessages = {}
    # Read dependent queue
    for speaker in self.motion_dict[entity]:
      dependentMessages[speaker] = ""
      while True:
        try:
          notification = self.dependentQueues[speaker].popleft()
          self.log(notification)
          dependentMessages[speaker] += notification + " "
        except IndexError:
          break

    universalMessage = ""
    # Read univeral queue
    while True:
      try:
        notification = self.queue.popleft()
        self.log(notification)
        universalMessage += notification + " "
      except IndexError:
        break

    speakerNo = 0
    for speaker in self.motion_dict[entity]:
      message = ""
      if speakerNo == 0:
        if universalMessage != "":
          message = universalMessage + " "

      dependentMessage = dependentMessages[speaker]
      if dependentMessage != "":
        message +=dependentMessage
      if message != "":
        service = self.args["speakers"][speaker]["service"]
        service_entity_id = self.args["speakers"][speaker]["service_entity_id"]
        self.log("Send Message to Speaker " + service_entity_id)
        self.call_service(service, entity_id=service_entity_id, message=message)
      speakerNo +=1
 