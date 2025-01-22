# Android fragmentation and kernels
# Setting up the environment

In order to get all the needed packages to run the scripts, create a virtual environment from the provided _requirements.txt_.
For environment `venv`:
```
virtualenv venv
source venv/bin/activate 
pip install -r requirements.txt
```

The **FIRST** script expects a folder with extracted kernels.
This code is designed to aggregate information about kernels into Google Tables. It uses Python module gspread, which requires a setup of a Google service account for automatic spreadsheet access. 
Refer to this [support page](https://support.google.com/a/answer/7378726?hl=en) to learn how to create such an account.
Then, check out section ***For Bots: Using Service Account*** on this [gspread documentation page](https://docs.gspread.org/en/v6.1.3/oauth2.html#for-bots-using-service-account) in order to properly place JSON with credentials. Also, make sure to share access to the spreadsheet with the service account in case the document is not openly accessible. 

environment variables for root dir? provide spreadsheet name as arg?

**SECOND** (Model info) script uses rotating VPN so that GSMArena does not detect scraping. 


TODO: rerun the scripts
TODO: outline heuristics
# Related work 
TODO: list papers