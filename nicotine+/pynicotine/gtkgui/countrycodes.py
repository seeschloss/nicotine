# Copyright (C) 2009 quinox. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

def code2name(code):
	try:
		return lookup[code.lower()]
	except KeyError:
		return None

lookup = {
		'ad':'Andorra',
		'ae':'United Arab Emirates',
		'af':'Afghanistan',
		'ag':'Antigua & Barbuda',
		'ai':'Anguilla',
		'al':'Albania',
		'am':'Armenia',
		'an':'Netherlands Antilles',
		'ao':'Angola',
		'aq':'Antarctica',
		'ar':'Argentina',
		'as':'American Samoa',
		'at':'Austria',
		'au':'Australia',
		'aw':'Aruba',
		'az':'Azerbaijan',
		'ba':'Bosnia & Herzegovina',
		'bb':'Barbados',
		'bd':'Bangladesh',
		'be':'Belgium',
		'bf':'Burkina Faso',
		'bg':'Bulgaria',
		'bh':'Bahrain',
		'bi':'Burundi',
		'bj':'Benin',
		'bm':'Bermuda',
		'bn':'Brunei Darussalam',
		'bo':'Bolivia',
		'br':'Brazil',
		'bs':'Bahamas',
		'bt':'Bhutan',
		'bv':'Bouvet Island',
		'bw':'Botswana',
		'by':'Belarus',
		'bz':'Belize',
		'ca':'Canada',
		'cc':'Cocos (Keeling) Islands',
		'cd':'Democratic Republic of Congo',
		'cf':'Central African Republic',
		'cg':'Congo',
		'ch':'Switzerland',
		'ci':'Ivory Coast',
		'ck':'Cook Islands',
		'cl':'Chile',
		'cm':'Cameroon',
		'cn':'China',
		'co':'Colombia',
		'cr':'Costa Rica',
		'cs':'Czechoslovakia (former)',
		'cu':'Cuba',
		'cv':'Cape Verde',
		'cx':'Christmas Island',
		'cy':'Cyprus',
		'cz':'Czech Republic',
		'de':'Germany',
		'dj':'Djibouti',
		'dk':'Denmark',
		'dm':'Dominica',
		'do':'Dominican Republic',
		'dz':'Algeria',
		'ec':'Ecuador',
		'ee':'Estonia',
		'eg':'Egypt',
		'eh':'Western Sahara',
		'er':'Eritrea',
		'es':'Spain',
		'et':'Ethiopia',
		'eu':'Europe',
		'fi':'Finland',
		'fj':'Fiji',
		'fk':'Falkland Islands (Malvinas)',
		'fm':'Micronesia',
		'fo':'Faroe Islands',
		'fr':'France',
		'ga':'Gabon',
		'gb':'Great Britain',
		'gd':'Grenada',
		'ge':'Georgia',
		'gf':'French Guiana',
		'gh':'Ghana',
		'gi':'Gibraltar',
		'gl':'Greenland',
		'gm':'Gambia',
		'gn':'Guinea',
		'gp':'Guadeloupe',
		'gq':'Equatorial Guinea',
		'gr':'Greece',
		'gs':'South Georgia & South Sandwich Islands',
		'gt':'Guatemala',
		'gu':'Guam',
		'gw':'Guinea-Bissau',
		'gy':'Guyana',
		'hk':'Hong Kong',
		'hm':'Heard & McDonald Islands',
		'hn':'Honduras',
		'hr':'Croatia',
		'ht':'Haiti',
		'hu':'Hungary',
		'id':'Indonesia',
		'ie':'Ireland',
		'il':'Israel',
		'in':'India',
		'io':'British Indian Ocean Territory',
		'iq':'Iraq',
		'ir':'Iran',
		'is':'Iceland',
		'it':'Italy',
		'jm':'Jamaica',
		'jo':'Jordan',
		'jp':'Japan',
		'ke':'Kenya',
		'kg':'Kyrgyzstan',
		'kh':'Cambodia',
		'ki':'Kiribati',
		'km':'Comoros',
		'kn':'Saint Kitts & Nevis',
		'kp':'North Korea',
		'kr':'South Korea',
		'kw':'Kuwait',
		'ky':'Cayman Islands',
		'kz':'Kazakhstan',
		'la':'Laos',
		'lb':'Lebanon',
		'lc':'Saint Lucia',
		'li':'Liechtenstein',
		'lk':'Sri Lanka',
		'lr':'Liberia',
		'ls':'Lesotho',
		'lt':'Lithuania',
		'lu':'Luxembourg',
		'lv':'Latvia',
		'ly':'Libya',
		'ma':'Morocco',
		'mc':'Monaco',
		'md':'Moldova',
		'mg':'Madagascar',
		'mh':'Marshall Islands',
		'mk':'Macedonia',
		'ml':'Mali',
		'mm':'Myanmar',
		'mn':'Mongolia',
		'mo':'Macau',
		'mp':'Northern Mariana Islands',
		'mq':'Martinique',
		'mr':'Mauritania',
		'ms':'Montserrat',
		'mt':'Malta',
		'mu':'Mauritius',
		'mv':'Maldives',
		'mw':'Malawi',
		'mx':'Mexico',
		'my':'Malaysia',
		'mz':'Mozambique',
		'na':'Namibia',
		'nc':'New Caledonia',
		'ne':'Niger',
		'nf':'Norfolk Island',
		'ng':'Nigeria',
		'ni':'Nicaragua',
		'nl':'Netherlands',
		'no':'Norway',
		'np':'Nepal',
		'nr':'Nauru',
		'nu':'Niue',
		'nz':'New Zealand',
		'om':'Oman',
		'pa':'Panama',
		'pe':'Peru',
		'pf':'French Polynesia',
		'pg':'Papua New Guinea',
		'ph':'Philippines',
		'pk':'Pakistan',
		'pl':'Poland',
		'pm':'Saint Pierre & Miquelon',
		'pn':'Pitcairn',
		'pr':'Puerto Rico',
		'ps':'Occupied Palestinian Territory',
		'pt':'Portugal',
		'pw':'Palau',
		'py':'Paraguay',
		'qa':'Qatar',
		're':'Reunion',
		'ro':'Romania',
		'ru':'Russia',
		'rw':'Rwanda',
		'sa':'Saudi Arabia',
		'sb':'Solomon Islands',
		'sc':'Seychelles',
		'sd':'Sudan',
		'se':'Sweden',
		'sg':'Singapore',
		'sh':'Saint Helena',
		'si':'Slovenia',
		'sj':'Svalbard & Jan Mayen Islands',
		'sk':'Slovak Republic',
		'sl':'Sierra Leone',
		'sm':'San Marino',
		'sn':'Senegal',
		'so':'Somalia',
		'sr':'Suriname',
		'st':'Sao Tome & Principe',
		'sv':'El Salvador',
		'sy':'Syria',
		'sz':'Swaziland',
		'tc':'Turks & Caicos Islands',
		'td':'Chad',
		'tf':'French Southern Territories',
		'tg':'Togo',
		'th':'Thailand',
		'tj':'Tajikistan',
		'tk':'Tokelau',
		'tl':'Timor-Leste',
		'tm':'Turkmenistan',
		'tn':'Tunisia',
		'to':'Tonga',
		'tp':'East Timor',
		'tr':'Turkey',
		'tt':'Trinidad & Tobago',
		'tv':'Tuvalu',
		'tw':'Taiwan',
		'tz':'Tanzania',
		'ua':'Ukraine',
		'ug':'Uganda',
		'um':'U.S. Minor Outlying Islands',
		'us':'United States',
		'uy':'Uruguay',
		'uz':'Uzbekistan',
		'va':'Holy See (Vatican City State)',
		'vc':'Saint Vincent & The Grenadines',
		've':'Venezuela',
		'vg':'British Virgin Islands',
		'vi':'U.S. Virgin Islands',
		'vn':'Viet Nam',
		'vu':'Vanuatu',
		'wf':'Wallis & Futuna',
		'ws':'Samoa',
		'ye':'Yemen',
		'yt':'Mayotte',
		'yu':'Yugoslavia (former)',
		'za':'South Africa',
		'zm':'Zambia',
		'zw':'Zimbabwe',
	}
