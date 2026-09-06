# Security model

`lai-gateway` is a private adapter. It must not become a second authority plane.

Current rules:

- keep the LAI control token server-side;
- never return the token to browsers, chat clients, logs, or model prompts;
- connect to the harness only through an explicit loopback HTTP origin;
- bind the gateway only to loopback in this MVP;
- expose no generic shell;
- expose no direct llama.cpp proxy;
- expose no commit, push, merge, tag, release, or pull-request authority;
- expose no run creation until authentication and approval boundaries exist.

The initial gateway is read-only from the client side. That is boring. Boring is underrated when credentials are involved.
