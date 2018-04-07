#!/usr/bin/env python

# import meetup.api
import p2k16.core.boot

p2k16.core.boot.model_should_use_flask = False
p2k16.core.boot.model_should_use_version_tables = False

trygvis_key = "776c37f342a65b1a5a7352b245e45"
# meetup = meetup.api.Client(api_key=trygvis_key)
#
# group_info = meetup.GetGroup({"urlname": "Bitraf"})
#
# print("keys={}".format(group_info.__dict__.keys()))
#
# events = meetup.GetEvents(group_urlname="Bitraf")
# # print("keys={}".format(events.__dict__.keys()))
# print("got #{} events".format(len(events.results)))
#
# # for event in events.results:  # type: Mapping[str, str]
# #     # print("keys={}".format(event.keys()))
# #
# #     d = event["description"]
# #     print(d)

import requests

urlname="Bitraf"

query = {
    "key": trygvis_key
}

req = requests.request("GET", "https://api.meetup.com/{}/events".format(urlname), params=query)

print("{}".format(req.status_code))
