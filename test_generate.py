#!/usr/bin/env python3
"""Test script to directly test the generate endpoint"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, process_generate
import uuid
import json

# Test data
test_data = {
    "partner_type": "openwrap",
    "client_name": "Rediads",
    "DFP_NETWORK_CODE": "23202412718",
    "DFP_USER_EMAIL_ADDRESS": "jatin@rediads.com",
    "DFP_ADVERTISER_NAME": "OpenWrap",
    "DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST": True,
    "DFP_ADVERTISER_TYPE": "ADVERTISER",
    "DFP_ORDER_NAME": "Interstitial_unsafe_test",
    "DFP_USE_EXISTING_ORDER_IF_EXISTS": False,
    "LINE_ITEM_PREFIX": "Interstitial_unsafe",
    "DFP_LINEITEM_TYPE": "PRICE_PRIORITY",
    "DFP_SAME_ADV_EXCEPTION": False,
    "DFP_DELIVERY_RATE_TYPE": "",
    "DFP_ROADBLOCK_TYPE": "AS_MANY_AS_POSSIBLE",
    "DFP_CURRENCY_CODE": "USD",
    "CURRENCY_EXCHANGE": False,
    "PREBID_BIDDER_CODE": "",
    "DFP_TARGETED_PLACEMENT_NAMES": "",
    "DFP_TARGETED_GEO": "",
    "DFP_DEVICE_CATEGORIES": "",
    "OPENWRAP_BUCKET_CSV": "Inline_Header_Bidding_Dense.csv",
    "pb_precision": 2,
    "pb_min": 8,
    "pb_max": 20,
    "pb_increment": 0.5,
    "DFP_NUM_CREATIVES_PER_LINE_ITEM": 1,
    "OPENWRAP_SETUP_TYPE": "WEBINTERSTITIAL",
    "OPENWRAP_CUSTOM_SETUP_TYPE": "",
    "OPENWRAP_USE_1x1_CREATIVE": False,
    "OPENWRAP_CREATIVE_TEMPLATE": "",
    "OPENWRAP_NATIVE_CREATIVE_USER_DEFINED_VAR": "",
    "VIDEO_LENGTHS": "",
    "ADPOD_SLOTS": "",
    "VIDEO_POSITION_TYPE": "",
    "ENABLE_DEAL_LINEITEM": False,
    "DEAL_CONFIG_TYPE": "",
    "DEAL_CONFIG": "",
    "ADPOD_CREATIVE_CACHE_URL": "https://ow.pubmatic.com",
    "DFP_PLACEMENT_SIZES": [
        {"width": "320", "height": "480"},
        {"width": "300", "height": "250"}
    ]
}

if __name__ == "__main__":
    print("=" * 80)
    print("Testing process_generate function directly...")
    print("=" * 80)
    
    job_id = str(uuid.uuid4())
    print(f"Job ID: {job_id}")
    print(f"Test data keys: {list(test_data.keys())}")
    print("\nStarting process_generate...")
    print("-" * 80)
    
    try:
        process_generate(job_id, test_data)
        print("\n" + "=" * 80)
        print("process_generate completed (check logs for details)")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

