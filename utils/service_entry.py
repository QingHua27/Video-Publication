"""Independent Windows service entry: durable logs, no terminal lifetime dependency."""
import argparse
import faulthandler
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from datetime import datetime,timezone


def main():
    parser=argparse.ArgumentParser();parser.add_argument('role',choices=['backend','frontend']);parser.add_argument('--node')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];os.chdir(root);sys.path.insert(0,str(root))
    logs=root/'logs';logs.mkdir(exist_ok=True)
    def record(event,**details):
        with (logs/'service-lifecycle.log').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(dict(time=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),role=args.role,event=event,**details),ensure_ascii=False)+'\n')
    with (logs/f'{args.role}.out.log').open('a',encoding='utf-8',buffering=1) as output,(logs/f'{args.role}.err.log').open('a',encoding='utf-8',buffering=1) as error:
        sys.stdout=output;sys.stderr=error;faulthandler.enable(file=error,all_threads=True)
        record('started')
        try:
            if args.role=='backend':
                from utils.ks_collection_tasks import resume
                resume()
                sys.argv=['flask','--app','sau_backend','run','--host','127.0.0.1','--port','5409']
                runpy.run_module('flask',run_name='__main__')
                record('exited',code=0)
            else:
                if not args.node:raise RuntimeError('Missing Node.js executable')
                result=subprocess.run([args.node,'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','5173','--strictPort'],cwd=root/'sau_frontend',stdout=output,stderr=error,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                record('exited',code=result.returncode)
                return result.returncode
        except BaseException as problem:
            record('exception',error=type(problem).__name__,message=str(problem));raise
        finally:
            faulthandler.disable();sys.stdout=sys.__stdout__;sys.stderr=sys.__stderr__
    return 0

if __name__=='__main__':sys.exit(main())
