from ..models import Queue as db_queue
from kombu import Consumer, Exchange, Connection
from kombu import Queue as celery_queue 

class QueueCollection:
    
    def __init__(self):
        self.queues = []
        all_db_queues = db_queue.objects.all()
        for d_queue in all_db_queues:
            q_name = d_queue.fullname
            c_queue = celery_queue(name=q_name, exchange=Exchange(''), routing_key=q_name, durable=True)
            self.queues.append(c_queue)
            print(f"Queue '{q_name}' declared")
        
    def get_queues(self, predicate = None):
        result = []
        if(predicate == None):
            predicate = lambda q: True
        for queue in self.queues:
            if(predicate(queue)):
                result.append(queue)

        return result
        