import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLEADS_YAML_FILE = os.path.join(ROOT_DIR, 'googleads.yaml')

#########################################################################
# DFP SETTINGS
#########################################################################

DFP_ORDER_NAME = 'Interstitial_unsafe_New_v09'
DFP_USER_EMAIL_ADDRESS = ''
DFP_ADVERTISER_NAME = 'OpenWrap'
DFP_ADVERTISER_TYPE = 'ADVERTISER'
DFP_LINEITEM_TYPE = 'PRICE_PRIORITY'
DFP_TARGETED_PLACEMENT_NAMES = []
DFP_PLACEMENT_SIZES = [{'width': '320', 'height': '480'}, {'width': '300', 'height': '250'}]
DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST = True
DFP_USE_EXISTING_ORDER_IF_EXISTS = True
DFP_NUM_CREATIVES_PER_LINE_ITEM = 1
DFP_CURRENCY_CODE = 'USD'
DFP_SAME_ADV_EXCEPTION = False
DFP_DEVICE_CATEGORIES = None
DFP_ROADBLOCK_TYPE = 'AS_MANY_AS_POSSIBLE'
DFP_TARGETED_GEO = []
LINE_ITEM_PREFIX = 'Interstitial_unsafe_New_v09'

#########################################################################
# PREBID/OPENWRAP SETTINGS
#########################################################################

PREBID_BIDDER_CODE = None
OPENWRAP_BUCKET_CSV = 'Inline_Header_Bidding_High.csv'
OPENWRAP_SETUP_TYPE = 'WEBINTERSTITIAL'
OPENWRAP_USE_1x1_CREATIVE = False
OPENWRAP_CREATIVE_TEMPLATE = None
OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR = None
CURRENCY_EXCHANGE = False
VIDEO_LENGTHS = []
ADPOD_SLOTS = []
ENABLE_DEAL_LINEITEM = False
DEAL_CONFIG_TYPE = None
DEAL_CONFIG = None
VIDEO_POSITION_TYPE = None
ADPOD_CREATIVE_CACHE_URL = 'https://ow.pubmatic.com'