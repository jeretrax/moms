import tempfile
import unittest
from finding_store import Store
from review_workflow import Workflow

class ReviewTests(unittest.TestCase):
 def test_approval_and_history(self):
  with tempfile.TemporaryDirectory() as d:
   path=d+'/test.db';s=Store(path)
   with s.db:s.add('a','finding',{'title':'test'},'operator','f')
   w=Workflow(s)
   def apply(event,data,role='operator'):
    return w.apply('a','r',len(w.history('a','r')),'tester',role,event,data)
   apply('created',{'items':['f']})
   with self.assertRaises(ValueError):w.apply('b','r',0,'tester','operator','created',{'items':['f']})
   apply('sent',{'delivery_reference':'fixture:delivered'})
   apply('responses_recorded',{'answers':{'f':{'choice':'needs_changes'}}},'customer')
   with self.assertRaises(ValueError):apply('implementation_recorded',{})
   apply('confirmation_reviewed',{'outcomes':{'f':{'outcome':'confirmed_issue','evidence':['fixture:answer']}}})
   proposal={'changes':[{'finding_id':'f','target':'https://example.com','before':'old','after':'new','reason':'confirmed'}]}
   result=apply('proposal_prepared',proposal);ph=result['data']['proposal_hash']
   with self.assertRaises(ValueError):apply('customer_approved',{'proposal_hash':ph},'customer')
   apply('internally_reviewed',{'proposal_hash':ph})
   with self.assertRaises(ValueError):apply('customer_approved',{'proposal_hash':'wrong'},'customer')
   apply('customer_approved',{'proposal_hash':ph},'customer')
   result=apply('proposal_prepared',{'changes':[dict(proposal['changes'][0],after='revised')]})
   with self.assertRaises(ValueError):apply('implementation_recorded',{'proposal_hash':ph})
   ph=result['data']['proposal_hash'];apply('internally_reviewed',{'proposal_hash':ph});apply('customer_approved',{'proposal_hash':ph},'customer')
   with self.assertRaises(ValueError):apply('implementation_recorded',{'proposal_hash':ph})
   apply('implementation_recorded',{'proposal_hash':ph,'backup_reference':'fixture:backup','baseline_reference':'fixture:baseline','execution_reference':'fixture:execution'})
   with self.assertRaises(ValueError):apply('verification_recorded',{'passed':False,'evidence':['fixture:failed']})
   apply('verification_recorded',{'passed':True,'evidence':['fixture:verified']})
   apply('completion_reported',{'report_reference':'fixture:report'})
   count=len(w.history('a','r'));s.db.close();s=Store(path);w=Workflow(s)
   self.assertEqual(len(w.history('a','r')),count)
   with self.assertRaises(ValueError):w.apply('a','r',0,'tester','operator','sent',{})
   s.db.close()

if __name__=='__main__':unittest.main()
