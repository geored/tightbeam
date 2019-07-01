# Tightbeam
  ( Rerouting Github Webhooks )




1. Server app should be deployed with public ip address.

  - build docker server container with:
  
              # docker build -t [your dockerhub repo name]/[docker image name]:[tag name] .
              # docker push [your dockerhub repo name]/[docker image name]:[tag name]
  
  - run server docker image somewhere on cloud with public IP address

2. Client app should be deployed on your development environment.

  - build docker client container with:

              # docker build -t [your dockerhub repo name]/[docker image name]:[tag name] .
              # docker push [your dockerhub repo name]/[docker image name]:[tag name]
              
  - run client docker image on your local development environment or your cluster development environment and:

       - provide environment variable WS_SERVER which is url endpoint for server websocket server:

                          [ws|wss]://[server app url]/ws
       - provide environment variable URL_TRIGGER which is REST endpoint for starting build process or pipeline:

                          [http|https]://[cluster ip]/[generated]/[path]/[for]/[starting]/[pipeline|build]
         OR [ If you are using umb-client service ]:
         
                Enter URL for Sidecar UMB-Client service from which you can raise UMB events:
                          
                          [http]://localhost:8080/
             ( HTTP Method must be POST )
        
         OR [ if you are using client service ]:
         
                    Just enter empty string in URL_TRIGGER environment variable.
         
       - privide environment variable GH_BRANCH which is github branch name for your project code:

                          [github branch name]
