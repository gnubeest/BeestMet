###
# Copyright (c) 2020, Brian McCord
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json
import os
import sys
import datetime
import calendar
import requests
from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('BeestMet')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

bullet = ' \x0303•\x0f '
pink = "\x0313"
green = "\x0303"
bol = '\x02'
nul = "\x0F"
itl = '\x1D'

class BeestMet(callbacks.Plugin):
    """get weather data"""
    pass

    def metar(self, irc, msgs, args, station):
        """[<station>]
            Get current METAR data for <station>.
        """

        avwx = self.registryValue('avwxKey')
        headers = {'Authorization': avwx}
        try:
            met_reply = (requests.get('https://avwx.rest/api/metar/' + station, headers=headers)).json()
        except:
            irc.error('No response from requested station')
            return
        try:
            irc.reply(met_reply['raw'])
        except KeyError:
            irc.error('Invalid ICAO code')

    metar = wrap(metar, ['something'])

    def nick_arg(self, my_nick, nick_inp):
        met_nick = ''
        try:
            metdb = json.load(open("{0}/met.json".format(os.path.dirname
                     (os.path.abspath(__file__)))))
        except FileNotFoundError:
            #irc.error('met.json not found')
            return
        if not nick_inp:
            nick_inp = metdb.get(my_nick)
            if not nick_inp:
                met_nick = 'error'
                nick_inp = 'error'
                return met_nick, nick_inp
        if metdb.get(nick_inp):
            met_nick = "\x0314/" + nick_inp
            nick_inp = metdb.get(nick_inp)
        return met_nick, nick_inp

    def quest(self, loc): # openmapquest geo lookup
        map_key = self.registryValue('mqKey')
        map_load = {'location': loc, 'key': map_key}
        map_data = (requests.get(
                    'http://open.mapquestapi.com/geocoding/v1/address',
                    params=map_load).json())
        map_result = map_data['results'][0]['locations'][0]
        map_lat = map_result['latLng']['lat']
        map_lon = map_result['latLng']['lng']

        ## reliability threshold
        #if (map_result['geocodeQualityCode'] ==
        #    'A1XXX'):
        #    irc.error('I cannot find reliable location data for \x0306' +
        #              loc_input + '\x0F.')
        #    return 'fail'

        ar_ar = ['adminArea1', 'adminArea2', 'adminArea3', 'adminArea4',
                 'adminArea5', 'adminArea6']
        area = []
        for ar_ix in range(0, 6):
            try:
                ar_val = map_result[ar_ar[ar_ix]]
                if ar_val:
                    area.append(ar_val)
            except KeyError:
                continue
        loc_str = "\x0314" + str(':'.join(area))
        return map_lat, map_lon, loc_str

    def met(self, irc, msgs, args, loc_input):
        """[<location>]
            Get current weather at <location>.
        """

        def current(lat, lon, loc): # get current weather, build output
            owm_key = self.registryValue('owKey')
            owm_load = {'lat': lat, 'lon': lon, 'appid': owm_key}
            owm_data = (requests.get(
                        'http://api.openweathermap.org/data/2.5/weather',
                        params=owm_load).json())
            unix_off = owm_data['timezone']
            unix_cur = datetime.datetime.now().timestamp()
            unix_sta = unix_cur + unix_off
            cur_time = datetime.datetime.fromtimestamp(unix_sta)
            time_str = cur_time.strftime("%H:%M")
            sky = owm_data['weather'][0]
            temps = owm_data['main']
            city = owm_data['name']
            if not city:
                city = 'unidentified station'
            wind = owm_data['wind']
            #sky_main = sky.get('main')
            sky_desc = sky.get('description')
            temp_cur = ("{:.0f}".format(temps.get('temp') - 273.15) + "°C")
            temp_f = ("{:.0f}".format(temps.get('temp') * 9 / 5 - 459.67) + "°F")
            #temp_lo = temps.get('temp_min')
            #temp_hi = temps.get('temp_max')
            #baro = temps.get('pressure')
            humid = temps.get('humidity')
            feels = ("{:.0f}".format(temps.get('feels_like') - 273.15) + "°C")
            try:
                vis = ("{:.1f}".format(owm_data.get('visibility') / 1000)
                               + "km")
            except TypeError:
                vis = 'unknown'
            wind_spd = wind.get('speed')
            wind_dir = wind.get('deg')
            if wind_dir:
                dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW',
                        'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
                ix = round(wind_dir / (360. / len(dirs)))
                ordinal = ' ' + (dirs[ix % len(dirs)])
            else:
                ordinal = ''
            c = ':'
            reply_str = (green + '▶' + pink + bol + city +
                         "\x0F weather " + itl + green + 'at ' + time_str +
                         '\x0F\x0303' + bullet + str(temp_cur) + " (" +
                         temp_f + ')' + bullet + sky_desc +
                         bullet + 'feels like ' + feels + bullet + str(humid) +
                         '% humidity' + bullet + 'winds' + ordinal + " at " +
                         str(wind_spd) + 'm/s' + bullet + "visibility " +
                         str(vis) + bullet + loc)
            return reply_str

        my_nick = msgs.nick
        print_nick, nick_done = self.nick_arg(my_nick, loc_input)
        if print_nick == 'error':
            irc.error('See the administrator to register your location.')
            return
        geo = self.quest(nick_done)
        #if geo == 'fail':
        #    return
        if (geo[0] == 39.78373) and (geo[1] == -100.445882):
            irc.reply('Sorry, I can\'t find your location.')
            return
        reply_str = current(geo[0], geo[1], geo[2])
        irc.reply(reply_str + print_nick, prefixNick=False)

    met = wrap(met, [optional('text')])

    def forecast(self, irc, msgs, args, loc_input):
        """[<location>]
            Get forecast for <location>.
        """

        def seven(lat, lon, loc): # 5-day forecast
            owm_key = self.registryValue('owKey')
            owm_load = {'lat': lat, 'lon': lon, 'exclude':
                        'current,minutely,hourly', 'appid': owm_key}
            owm_data = (requests.get(
                        'http://api.openweathermap.org/data/2.5/onecall',
                        params=owm_load).json())
            ow2_load = {'lat': lat, 'lon': lon, 'appid': owm_key}
            ow2_data = (requests.get(
                        'http://api.openweathermap.org/data/2.5/weather',
                        params=ow2_load).json())
            city = ow2_data['name']
            sky = ow2_data['weather'][0]
            temps = ow2_data['main']
            if not city:
                city = 'unidentified station'
            sky_desc = sky.get('main')
            temp_cur = ("{:.0f}".format(temps.get('temp') - 273.15) + "°C")
            temp_f = ("{:.0f}".format(temps.get('temp') * 9 / 5 - 459.67) + "°F")

            fc_str = (green + '▶' + pink + bol + city + nul + ' forecast' +
                      bullet + itl + green + "Now " + nul + sky_desc + ', ' +
                      temp_cur + ' (' + temp_f + ')')

            for fc_day in range(0, 6):
                fc_fc = owm_data['daily'][fc_day]
                fc_date = fc_fc['dt']
                fc_lo = "{:.0f}".format(fc_fc['temp']['min'] - 273.15)
                fc_hi = "{:.0f}".format(fc_fc['temp']['max'] - 273.15)
                fc_cond = fc_fc['weather'][0]['main']
                fc_wkdy = (datetime.datetime.fromtimestamp
                           (int(fc_date)).strftime('%a'))
                if fc_day == 0:
                    fc_wkdy = 'Later'
                fc_str = (fc_str + bullet + "\x0303" + fc_wkdy + "\x0F " +
                          fc_cond + ", " + str(fc_lo) + "-" +
                          str(fc_hi)) + "°C"
            fc_str = fc_str + bullet + loc
            return fc_str
            
        my_nick = msgs.nick
        print_nick, nick_done = self.nick_arg(my_nick, loc_input)
        if print_nick == 'error':
            irc.error('See the administrator to register your location.')
            return
        geo = self.quest(nick_done)
        #if geo == 'fail':
        #    return
        reply_str = seven(geo[0], geo[1], geo[2])
        irc.reply(reply_str + print_nick, prefixNick=False)

    forecast = wrap(forecast, [optional('text')])

Class = BeestMet


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
