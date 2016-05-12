# -*- coding: utf-8 -*-
#
#    LinOTP - the open source solution for two factor authentication
#    Copyright (C) 2010 - 2015 LSE Leading Security Experts GmbH
#
#    This file is part of LinOTP server.
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#    E-mail: linotp@lsexperts.de
#    Contact: www.linotp.org
#    Support: www.lsexperts.de
#


"""
Test for check_status, which could be used to support polling
"""

import json
import logging
import datetime

from linotp.tests import TestController

log = logging.getLogger(__name__)


class TestCheckStatus(TestController):

    def setUp(self):
        TestController.setUp(self)
        # clean setup
        self.delete_all_policies()
        self.delete_all_token()
        self.delete_all_realms()
        self.delete_all_resolvers()

        # create the common resolvers and realm
        self.create_common_resolvers()
        self.create_common_realms()
        return

    def tearDown(self):
        TestController.tearDown(self)

    def create_hmac_token(self, user='root', pin='pin', serial='F722362',
                          otpkey="AD8EABE235FC57C815B26CEF3709075580B44738"):
        """
        create simple hmac token  with 10 known values
        """
        otps = [
            "870581",
            "793334",
            "088491",
            "013126",
            "818771",
            "454594",
            "217219",
            "250710",
            "478893",
            "517407"
        ]

        parameters = {"serial": serial,
                      "otpkey": otpkey,
                      "user": user,
                      "pin": pin,
                      "description": "check_status" + serial,
                      }

        response = self.make_admin_request('init', params=parameters)
        self.assertTrue('"value": true' in response, response)

        return serial, otps


###############################################################################
    def test_single_token(self):
        '''
        setup hmac token to support multiple challenges
        '''
        policy = {'name': 'hmac_challenge_response',
                  'scope': 'authentication',
                  'action': 'challenge_response=hmac',
                  'realm': '*',
                  'user': '*',
                  }

        # define challenge response for hmac token
        response = self.make_system_request('setPolicy', params=policy)
        self.assertTrue('"status": true' in response, response)

        param = {'DefaultChallengeValidityTime': '120'}
        response = self.make_system_request('setConfig', params=param)
        self.assertTrue('"status": true' in response, response)

        serial, otps = self.create_hmac_token(user='passthru_user1',
                                              pin='123!')

        # trigger challenge
        params = {'user': 'passthru_user1',
                  'pass': '123!'}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": false' in response, response)

        # and extract the transaction id
        jresp = json.loads(response.body)
        transid = jresp.get('detail', {}).get('transactionid', None)
        self.assertTrue(transid is not None, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)
        self.assertTrue('"received_tan": false' in response, response)
        self.assertTrue('"valid_tan": false' in response, response)
        self.assertTrue('"received_count": 0, ' in response, response)

        # invalidate request
        params = {'user': 'passthru_user1',
                  'pass': '112233',
                  'transactionid': transid}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": false' in response, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)
        self.assertTrue('"received_tan": true' in response, response)
        self.assertTrue('"valid_tan": false' in response, response)
        self.assertTrue('"received_count": 1, ' in response, response)

        # validate request
        params = {'user': 'passthru_user1',
                  'pass': otps[0],
                  'transactionid': transid}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": true' in response, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)

        self.assertTrue('"received_tan": true' in response, response)
        self.assertTrue('"valid_tan": true' in response, response)
        self.assertTrue('"received_count": 2, ' in response, response)

        # verify that the challenge expires
        param = {'DefaultChallengeValidityTime': '1'}
        response = self.make_system_request('setConfig', params=param)
        self.assertTrue('"status": true' in response, response)

        start = datetime.datetime.now()
        try:
            while True:

                # now check for the status
                params = {'user': 'passthru_user1',
                          'pass': '123!',
                          'transactionid': transid}

                response_stat = self.make_validate_request('check_status',
                                                           params)
                if '"value": false' in response_stat:
                    break

                now = datetime.datetime.now()
                self.assertTrue(now < start + datetime.timedelta(seconds=3),
                                "challenge did not expire: %r" % response)

        finally:
            # reset to default expiration time
            param = {'DefaultChallengeValidityTime': '120'}
            response = self.make_system_request('setConfig', params=param)
            self.assertTrue('"status": true' in response, response)

        self.delete_token(serial)
        self.delete_policy('hmac_challenge_response')

        return

    def test_multiple_token(self):
        '''
        test for check_status with multiple hmac token in challenge response
        '''
        policy = {'name': 'hmac_challenge_response',
                  'scope': 'authentication',
                  'action': 'challenge_response=hmac',
                  'realm': '*',
                  'user': '*',
                  }

        # define challenge response for hmac token
        response = self.make_system_request('setPolicy', params=policy)
        self.assertTrue('"status": true' in response, response)

        param = {'DefaultChallengeValidityTime': '120'}
        response = self.make_system_request('setConfig', params=param)
        self.assertTrue('"status": true' in response, response)

        serial, otps = self.create_hmac_token(user='passthru_user1',
                                              pin='123!')

        otpkey2 = "6CEF3709075580B44738AD8EABE235FC57C815B2"
        serial2, _otps = self.create_hmac_token(user='passthru_user1',
                                                pin='123!',
                                                serial=serial + '_2',
                                                otpkey=otpkey2)

        # trigger challenge
        params = {'user': 'passthru_user1',
                  'pass': '123!'}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": false' in response, response)

        # and extract the transaction id
        jresp = json.loads(response.body)
        transid = jresp.get('detail', {}).get('transactionid', None)
        self.assertTrue(transid is not None, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)
        self.assertTrue('"received_tan": false' in response, response)
        self.assertTrue('"valid_tan": false' in response, response)
        self.assertTrue('"received_count": 0, ' in response, response)

        self.assertTrue('"received_tan": true' not in response, response)
        self.assertTrue('"valid_tan": true' not in response, response)

        # invalidate request
        params = {'user': 'passthru_user1',
                  'pass': '112233',
                  'transactionid': transid}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": false' in response, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)
        self.assertTrue('"received_tan": true' in response, response)
        self.assertTrue('"valid_tan": false' in response, response)
        self.assertTrue('"received_count": 1, ' in response, response)

        self.assertTrue('"valid_tan": true' not in response, response)
        self.assertTrue('"received_count": 0, ' not in response, response)
        self.assertTrue('"received_tan": false' not in response, response)

        # validate request
        params = {'user': 'passthru_user1',
                  'pass': otps[0],
                  'transactionid': transid}
        response = self.make_validate_request('check', params)
        self.assertTrue('"value": true' in response, response)

        # now check for the status
        params = {'user': 'passthru_user1',
                  'pass': '123!',
                  'transactionid': transid}

        response = self.make_validate_request('check_status', params)

        self.assertTrue('"received_tan": true' in response, response)
        self.assertTrue('"valid_tan": true' in response, response)
        self.assertTrue('"valid_tan": false' in response, response)
        self.assertTrue('"received_count": 2, ' in response, response)
        self.assertTrue('"received_count": 1, ' in response, response)

        # verify that the challenge expires
        param = {'DefaultChallengeValidityTime': '1'}
        response = self.make_system_request('setConfig', params=param)
        self.assertTrue('"status": true' in response, response)

        start = datetime.datetime.now()
        try:
            while True:

                # now check for the status
                params = {'user': 'passthru_user1',
                          'pass': '123!',
                          'transactionid': transid}

                response_stat = self.make_validate_request('check_status',
                                                           params)
                if '"value": false' in response_stat:
                    break

                now = datetime.datetime.now()
                self.assertTrue(now < start + datetime.timedelta(seconds=3),
                                "challenge did not expire: %r" % response)

        finally:
            # reset to default expiration time
            param = {'DefaultChallengeValidityTime': '120'}
            response = self.make_system_request('setConfig', params=param)
            self.assertTrue('"status": true' in response, response)

        self.delete_token(serial)
        self.delete_token(serial2)
        self.delete_policy('hmac_challenge_response')

        return

# eof #########################################################################