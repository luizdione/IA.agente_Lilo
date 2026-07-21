---
name: tornado
description: Servidor HTTP assincrono, websockets e utilitarios IO.
triggers: ['tornado', 'http', 'websocket', 'async', 'ioloop']
functions: 34
source: lilo_skills/registry.json
---

# tornado


Funcoes expostas via `lilo_skills` (34 no total). Cada uma e um wrapper validado contra `schemas/<funcao>.json` e e chamada via MCP tool `lilo_run_skill` ou import direto:


```python
from lilo_skills import run_skill
res = run_skill("autoreload_main", **kwargs)
```


## Funcoes

- **auth_url_concat** -- `tornado.auth.url_concat` -- 2 parametro(s) [manipulacao_dados]
- **autoreload_add_reload_hook** -- `tornado.autoreload.add_reload_hook` -- 1 parametro(s) [bioinformatica, manipulacao_dados]
- **autoreload_main** -- `tornado.autoreload.main` -- 0 parametro(s) [bioinformatica, estatistica, manipulacao_dados]
- **autoreload_start** -- `tornado.autoreload.start` -- 1 parametro(s) [estatistica]
- **autoreload_wait** -- `tornado.autoreload.wait` -- 0 parametro(s) [estatistica]
- **autoreload_watch** -- `tornado.autoreload.watch` -- 1 parametro(s) [geral]
- **concurrent_chain_future** -- `tornado.concurrent.chain_future` -- 2 parametro(s) [bioinformatica, manipulacao_dados]
- **concurrent_future_set_exc_info** -- `tornado.concurrent.future_set_exc_info` -- 2 parametro(s) [bioinformatica, estatistica, manipulacao_dados]
- **concurrent_run_on_executor** -- `tornado.concurrent.run_on_executor` -- 2 parametro(s) [bioinformatica, manipulacao_dados]
- **escape_json_decode** -- `tornado.escape.json_decode` -- 1 parametro(s) [geral]
- **escape_json_encode** -- `tornado.escape.json_encode` -- 1 parametro(s) [geral]
- **escape_native_str** -- `tornado.escape.native_str` -- 1 parametro(s) [manipulacao_dados]
- **escape_recursive_unicode** -- `tornado.escape.recursive_unicode` -- 1 parametro(s) [manipulacao_dados]
- **escape_squeeze** -- `tornado.escape.squeeze` -- 1 parametro(s) [bioinformatica]
- **escape_to_basestring** -- `tornado.escape.to_basestring` -- 1 parametro(s) [manipulacao_dados]
- **escape_to_unicode** -- `tornado.escape.to_unicode` -- 1 parametro(s) [manipulacao_dados]
- **escape_url_escape** -- `tornado.escape.url_escape` -- 2 parametro(s) [geral]
- **escape_utf8** -- `tornado.escape.utf8` -- 1 parametro(s) [manipulacao_dados]
- **escape_xhtml_escape** -- `tornado.escape.xhtml_escape` -- 1 parametro(s) [geral]
- **escape_xhtml_unescape** -- `tornado.escape.xhtml_unescape` -- 1 parametro(s) [geral]
- **gen_chain_future** -- `tornado.gen.chain_future` -- 2 parametro(s) [bioinformatica, manipulacao_dados]
- **gen_convert_yielded** -- `tornado.gen.convert_yielded` -- 1 parametro(s) [bioinformatica, manipulacao_dados]
- **gen_coroutine** -- `tornado.gen.coroutine` -- 1 parametro(s) [bioinformatica]
- **gen_future_set_exc_info** -- `tornado.gen.future_set_exc_info` -- 2 parametro(s) [bioinformatica, estatistica, manipulacao_dados]
- **gen_is_coroutine_function** -- `tornado.gen.is_coroutine_function` -- 1 parametro(s) [geral]
- **gen_isawaitable** -- `tornado.gen.isawaitable` -- 1 parametro(s) [geral]
- **gen_maybe_future** -- `tornado.gen.maybe_future` -- 1 parametro(s) [manipulacao_dados]
- **gen_multi** -- `tornado.gen.Multi` -- 2 parametro(s) [estatistica, matematica]
- **gen_multi_future** -- `tornado.gen.multi_future` -- 2 parametro(s) [bioinformatica]
- **gen_overload** -- `tornado.gen.overload` -- 1 parametro(s) [manipulacao_dados]
- **gen_singledispatch** -- `tornado.gen.singledispatch` -- 1 parametro(s) [bioinformatica, manipulacao_dados]
- **gen_sleep** -- `tornado.gen.sleep` -- 1 parametro(s) [matematica]
- **http1connection_native_str** -- `tornado.http1connection.native_str` -- 1 parametro(s) [manipulacao_dados]
- **http1connection_utf8** -- `tornado.http1connection.utf8` -- 1 parametro(s) [manipulacao_dados]
