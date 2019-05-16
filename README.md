# tightbeam

1. Server app should be deployed with public ip address.

2. Client app should be deployed on your development environment.
  - provide environment variable WS_SERVER which is url endpoint for server websocket server:
  
              [ws|wss]://[server app url]:8182/ws
  - provide environment variable URL_TRIGGER which is REST endpoint for starting build process or pipeline:
  
              [http|https]://[cluster ip]/[generated]/[path]/[for]/[starting]/[pipeline|build]
