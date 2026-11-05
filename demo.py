"""Synthetic portfolio for screenshots and development; never reads the host workspace."""
from datetime import datetime, timedelta, timezone


STARTED = datetime.now(timezone.utc)

def snapshot():
    now = STARTED
    stamp = lambda minutes=0: (now-timedelta(minutes=minutes)).isoformat()
    projects = [{'id':k,'name':n,'displayName':n,'path':'/demo/'+k,'kind':'git','remote':None,'core':True} for k,n in [('atlas','Atlas'),('garden','Garden')]]
    workspaces = []
    repositories = []
    for p in projects:
        dirty = p['id']=='atlas'
        files = [{'code':' M','path':'src/view.js'}, {'code':'??','path':'notes.md'}] if dirty else []
        workspaces.append({'repoId':p['id'],'path':p['path'],'label':'Primary checkout','primary':True,'branch':'feature/companion' if dirty else 'main','head':'demo-head','files':files,'fileCount':len(files),'tracked':1 if dirty else 0,'untracked':1 if dirty else 0,'conflicts':0,'error':None,'ignoredCount':0,'ignoredPaths':[],'upstream':None,'upstreamComparison':{'ahead':2,'behind':0} if dirty else None,'chatIds':['demo-approval'] if dirty else [],'checkedAt':stamp(),'tip':['demo','2026-11-04','Synthetic commit']})
        repositories.append({'id':p['id'],'root':p['path'],'remote':None,'name':p['name'],'branches':[{'name':workspaces[-1]['branch'],'sha':'demo-head','upstream':None}],'stashes':[]})
    base={'cwd':'/demo/atlas','archived':False,'pinned':False,'updatedAt':now.timestamp(),'projectIds':['atlas'],'workspacePaths':['/demo/atlas'],'assignedFolderExists':False,'request':'Review the compact navigation.','requestAt':stamp(5),'responseAt':stamp(2),'lastMessageAt':stamp(2),'lastEventAt':stamp(2),'lastActivityAt':stamp(2),'turnState':'finished','prs':[],'commits':[],'workdirs':[],'contextError':None,'historyLimited':True,'compactionsObserved':1,'model':'Example model','link':'#'}
    threads=[{**base,'id':'demo-approval','title':'Choose navigation behavior','response':'Remaining: this needs your approval before implementation.','telemetry':{'observedAt':stamp(2),'lastTokens':78000,'contextWindow':100000,'totalTokens':450000,'windows':[{'kind':'primary','minutes':300,'usedPercent':28,'resetsAt':int((now+timedelta(hours=2)).timestamp())}],'source':'Synthetic token_count event; illustrative values','cost':None}},
             {**base,'id':'demo-active','title':'Check keyboard navigation','response':'Verification still needs work.','requestAt':stamp(1),'turnState':'started','lastActivityAt':stamp(),'telemetry':None},
             {**base,'id':'demo-stale','title':'Review the earlier handoff','projectIds':['garden'],'workspacePaths':['/demo/garden'],'cwd':'/demo/garden','response':'Remaining: check the acceptance criteria.','lastActivityAt':stamp(120),'telemetry':{'observedAt':stamp(120),'lastTokens':None,'contextWindow':None,'totalTokens':123000,'windows':[{'kind':'secondary','minutes':10080,'usedPercent':50,'resetsAt':int((now-timedelta(hours=1)).timestamp())}],'source':'Synthetic stale event','cost':None}}]
    roadmaps=[{'projectId':p['id'],'sourceId':None,'sourcePolicy':'primary','documentIds':[],'alternates':[],'planIds':[],'warnings':[],'tasks':[]} for p in projects]
    data={'demo':True,'checkedAt':datetime.now(timezone.utc).isoformat(),'threads':threads,'projects':projects,'repositories':repositories,'workspaces':workspaces,'roadmaps':roadmaps,'documents':[],'source':{'schema':'synthetic','mode':'demo'},'coverage':{'chats':len(threads),'archived':0,'missingHistory':0},'github':{},'taskGitHub':{}}
    return data, {'repositories':[],'checkedAt':None}
