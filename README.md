# ACTFast 
*(**A**ngeles **C**omposite **T**ech **Fast**API)*

Small **FastAPI** based docker container to serve complex, transformed data from Epicor to ACTI custom applications.

Once deployed, the swagger UI can be accessed at 'http://&lt;hostname&gt;:8080/docs'

At the time of this update, ACTFast is being used for the insight/shopscreens efficiency project.


## WARNING

Updating this repo will cause a webhook push to portainer, reloading the stack. This will cause brief downtime for the application. 

# Notes

* There is a CNAME record in the ACTI DNS for 'actfast' that points to the docker host (atlas). 

* The settings.py contains easy to edit settings. Notably this also contains the dept_translate dict. Use this to translate JCDEPT's for emps to OprSeq's.

