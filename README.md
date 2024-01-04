# Cisco Data Miner Support Library
In order to use the module, you need to ensure its in the normal searh path.
Or, as id, you can add the path at runtme via:

## Add Cisco DataMiner Folder to system path
<code># Adding path for CDM
import sys
sys.path.insert(0, '../cdm')
</code>

## To the use the module, you wlll need to ensure the following vairables are set by your python3 applicaiton:
<code># Import CDM
import cdm
</code>

## Important Virables to initialize
<code># Initialize CDM
from cdm import tokenUrl	# Full path of oAuth endpoint: <protocolscheme><host><path>
from cdm import grantType	# Grant Type being used - defalt: client_credentials
from cdm import clientId	# Used to store the Client ID. Default is None
from cdm import clientSecret	# Used to store the Client Secret. Default is None
from cdm import cacheControl	# Cache control.  Default is no-cache
from cdm import authScope	# Specify the access level or permissions. Default is None
</code>
