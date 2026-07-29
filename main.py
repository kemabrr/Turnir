2026-07-29T05:50:05.547511171Z [inf]  Starting Container
2026-07-29T05:50:06.364688791Z [err]  Traceback (most recent call last):
2026-07-29T05:50:06.364715281Z [err]               ^^^^^^
2026-07-29T05:50:06.364718570Z [err]    File "/opt/venv/bin/uvicorn", line 8, in <module>
2026-07-29T05:50:06.364724290Z [err]      sys.exit(main())
2026-07-29T05:50:06.364755040Z [err]    File "/opt/venv/lib/python3.12/site-packages/click/core.py", line 1569, in __call__
2026-07-29T05:50:06.364763810Z [err]      return self.main(*args, **kwargs)
2026-07-29T05:50:06.365176437Z [err]    File "/opt/venv/lib/python3.12/site-packages/click/core.py", line 1353, in invoke
2026-07-29T05:50:06.365181917Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365187067Z [err]      return ctx.invoke(self.callback, **ctx.params)
2026-07-29T05:50:06.365192677Z [err]    File "/opt/venv/lib/python3.12/site-packages/click/core.py", line 1490, in main
2026-07-29T05:50:06.365196357Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365200327Z [err]      rv = self.invoke(ctx)
2026-07-29T05:50:06.365204927Z [err]           ^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365213867Z [err]    File "/opt/venv/lib/python3.12/site-packages/click/core.py", line 907, in invoke
2026-07-29T05:50:06.365219787Z [err]      return callback(*args, **kwargs)
2026-07-29T05:50:06.365615333Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365628443Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/main.py", line 410, in main
2026-07-29T05:50:06.365633883Z [err]      run(
2026-07-29T05:50:06.365638363Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/main.py", line 577, in run
2026-07-29T05:50:06.365642843Z [err]      server.run()
2026-07-29T05:50:06.365647123Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/server.py", line 65, in run
2026-07-29T05:50:06.365651662Z [err]      return asyncio.run(self.serve(sockets=sockets))
2026-07-29T05:50:06.365655292Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365659252Z [err]    File "/root/.nix-profile/lib/python3.12/asyncio/runners.py", line 194, in run
2026-07-29T05:50:06.365664522Z [err]      return runner.run(main)
2026-07-29T05:50:06.365668652Z [err]             ^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.365672192Z [err]    File "/root/.nix-profile/lib/python3.12/asyncio/runners.py", line 118, in run
2026-07-29T05:50:06.365675462Z [err]      return self._loop.run_until_complete(task)
2026-07-29T05:50:06.365679372Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.366661924Z [err]    File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
2026-07-29T05:50:06.366664884Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/server.py", line 69, in serve
2026-07-29T05:50:06.366668284Z [err]      await self._serve(sockets)
2026-07-29T05:50:06.366672134Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/server.py", line 76, in _serve
2026-07-29T05:50:06.366675044Z [err]      config.load()
2026-07-29T05:50:06.366677674Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/config.py", line 434, in load
2026-07-29T05:50:06.366680344Z [err]      self.loaded_app = import_from_string(self.app)
2026-07-29T05:50:06.366683364Z [err]                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.366741833Z [err]    File "/opt/venv/lib/python3.12/site-packages/uvicorn/importer.py", line 19, in import_from_string
2026-07-29T05:50:06.366744643Z [err]      module = importlib.import_module(module_str)
2026-07-29T05:50:06.366747593Z [err]               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.366751393Z [err]    File "/root/.nix-profile/lib/python3.12/importlib/__init__.py", line 90, in import_module
2026-07-29T05:50:06.366754503Z [err]      return _bootstrap._gcd_import(name[level:], package, level)
2026-07-29T05:50:06.367779204Z [err]             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.367783614Z [err]  ^^^^^^^^^^^^^^^^^^
2026-07-29T05:50:06.367786574Z [err]    File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
2026-07-29T05:50:06.367790064Z [err]    File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
2026-07-29T05:50:06.367793544Z [err]    File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
2026-07-29T05:50:06.367796394Z [err]    File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
2026-07-29T05:50:06.367799334Z [err]    File "<frozen importlib._bootstrap_external>", line 995, in exec_module
2026-07-29T05:50:06.367801964Z [err]    File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
2026-07-29T05:50:06.367804514Z [err]    File "/app/main.py", line 13, in <module>
2026-07-29T05:50:06.367807154Z [err]      from routers import auth, profile, payment, teams, turnir, admin, lobi
2026-07-29T05:50:06.367809724Z [err]  ImportError: cannot import name 'lobi' from 'routers' (/app/routers/__init__.py)
