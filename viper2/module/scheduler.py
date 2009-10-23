###############################################################################
# IMPORTS
###############################################################################
import time, threading, thread
import sys
import device
import config
from const import *

###############################################################################
# EVENT CLASS
###############################################################################
class Event(object):
  """
  Event class is a structure with accessors.
  This class is used to add new event to the Scheduler.
  """

  def __init__(self, device, delay, periodic, modifiedRegisters = None):
    """
    Constructor.
    @param device device to call when time is elapsed
    @param delay time to wait (seconds, float)
    @param modifiedRegisters list of modifiedRegisters to give to device (use by Ecu only)
    """
    self.__time   = delay
    self.__delay  = delay
    self.__device = device
    self.__modifiedRegisters = modifiedRegisters
    self._periodic = periodic
    if (self._periodic == true):
      self.__time = time.time()

  def getTime(self):
    """
    @return date the event will be launched
    """
    return self.__time
  
  def getDelay(self):
    """
    @return time to wait in seconds (float)
    """
    return self.__delay
    
  def setTime(self, time_):
    """
    Set time. This function is used by scheduler to speed up
    the time by instance.
    @param time_ new time to set.
    """
    self.__time = time_

  def getDevice(self):
    """
    @return device id
    """
    return self.__device

  def getModifiedRegisters(self):
    """
    @return modified registers mask
    """
    return self.__modifiedRegisters
    
###############################################################################
# SCHEDULER CLASS
###############################################################################
class Scheduler(object):
  """
  Logical scheduler
  All events are handle by this class.
  ?? There may have one instance of this class.
  """
  
  def __init__(self, speedCoeff):
    """
    Constructor.
    @param speedCoeff (floating variable) is the coeff to apply to the time.
	    3 means three times speeder
    """
    self.__speedCoeff = float(speedCoeff)
    self.__events     = [] # List
    self.__fps        = time.time()
    self.__run        = True
    self.__sem        = threading.Semaphore()
    self.__time       = 0
        
    """ Dispatch display on pygame or consol """
    from config import dispatch_display
    dispatch_display.scheduler(self)
              
  def addEvent(self, event):  
    """
    * Add event to the scheduler.
    * If periodic event, increment delay to last execution time
      If one shot event, increment delay to actual time
    * Insert event in the right place
    @param event the Event to add
    """    
    if (event._periodic == true):
      newtime = (event.getDelay() / self.__speedCoeff) + event.getTime()
    else:
      newtime = (event.getDelay() / self.__speedCoeff) + time.time()
    event.setTime(newtime)

    #print "sched.addEvent() - t:" + str(newtime - 1256045588)

    self.__sem.acquire()
    # TODO : Don't start the searching from the beginning of the list but by the middle (worst case in log(n) instead of n)
    length = len(self.__events)
    i = 0
    if (length > 0):
      for ev in range(length):
       oldtime = self.__events[ev].getTime()
       if (oldtime > newtime):
        break
       i = i + 1

    self.__events.insert(i,event)
    self.__sem.release()
     
  def start(self):
    """
    * If pygame, launch event received
    * Start scheduler : Get Event whose time is passed, call event()
      Device'method and remove the event from the list.
    * Sleep scheduler the min time to wait.
    """
    
    """ Init and start sorting thread """
    self.__sortingThread = SortingThread(self)
    self.__sortingThread.setDaemon(True) # Can stop script even if thread is running
    self.__sortingThread.start()
    self.__fps        = time.time()
        
    #sys.setcheckinterval(100)
    
    while self.__run:
     """
     * If pygame : wait for event
       Otherwise : Do nothing
     """
     self._pygameOrNotPygame()
         
  def withoutPygame(self):
    pass
    
  def withPygame(self):
     """
     * Waiting for events from the keyboard/mouse
     * Refresh display every 100ms ( 10 fps )
     """
     #t10 = time.time()
     #print "sched.withPygame() - start at t:" + str(time.time() - 1256045588)
     
     for event in pygame.event.get():
      if (event.type == pygame.QUIT):
        sys.exit()
      else:
          self._widg.event(event)  
     
     """ Display devices """
     for ecu in config.allEcus:
       for name, device in ecu._devices.iteritems():
         device.refresh_display()
     pygame.display.flip()
     #print "sched.withPygame() - end refresh display at t:" + str(time.time() - 1256045588)
     self.__fps += 0.1 # 10fps
       
     #t11 = time.time()
     #print "sched.withPygame() - t11-t10:" + str(t11-t10) + " - ttw:" + str(self.__fps-time.time()) + " t:" + str(time.time() - 1256045588)
     threading.Event().wait(self.__fps-time.time())
       
  def kill(self):
    """
    Stop scheduler
    """
    #TODO : dispatch kill too according to pygameOrNotPygame
    self.__run = False
    """Stop reading thread"""
    if self.__sortingThread:
      self.__sortingThread.kill()
      if self.__sortingThread.isAlive():
        print "Waiting sorting thread 1 seconde (it's may be waiting for next event)..."
        time.sleep(1)
    pygame.quit()

  def sortEvent(self):
     #t1 = time.time()
     #TODO : Check if better to use an other thread for event management
     """Event sorting..."""
     previousTime=0
     events	  = [] # List
     currentTime = time.time()
     for event in self.__events:
      if event.getTime() < currentTime:
       if event.getTime() != previousTime:
        events.append(event)
        previousTime=event.getTime()
    
     """...and lauching"""
     for event in events:
      self.__sem.acquire()
      #TODO: check if better somewhere else ?
      if (event._periodic == true):
        index = self.__events.index(event)
        self.__events[index].setTime(self.__events[index].getTime()+(self.__events[index].getDelay()/self.__speedCoeff))
        #print "sched.sortEvent() - t:" + str(self.__events[index].getTime() - 1256045588)
      else:
        self.__events.remove(event)
      self.__sem.release()
      event.getDevice().event(event.getModifiedRegisters())    
      
     self.__sem.acquire()
     ttw = self.__events[0].getTime()
     self.__sem.release()
     
     #t2 = time.time()
     #print "sched.sortEvent() - t2-t1:" + str(t2-t1) + " ttw:" + str(ttw-time.time()) + " t:" + str(time.time() - 1256045588)
     """Sleep until next event"""
     threading.Event().wait(ttw-time.time())
     
###############################################################################
# SORTING THREAD CLASS
###############################################################################
class SortingThread(threading.Thread):
  """
  
  """

  def __init__(self, sched):
    """
    Constructor.
    @param ipc ipc structure to access fifo with ipc_mod module
    @ecu ecu to add event.
    """
    threading.Thread.__init__(self)
    self.__sched = sched
    self.__run = True

  def run(self):
    """
    The threaded function.
    Wait that fifo is not empty.
    """
    
    while self.__run:
      """ Sort Events """
      self.__sched.sortEvent()
      
  def kill(self):
    """
    Call to stop the main loop of the sorting thread.
    """
    self.__run = False
    