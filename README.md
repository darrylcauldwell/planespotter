# Planespotter

Welcome to another home for the Planespotter application, a fully functional example cloud native application. The application is composes of five components, frontend, RESTful api, synchronizer, redis and mysql.  

The frontend and RESTful api are both written using the Python Flash microframework. The frontend presents content and the application manages the various connections. The sync funcationality is also written in Python and performs live data syncronizion of aircrafts that are currently airborne, this data is then cached in Redis. The MySQL database is populated at point of deployment with Aircraft data pulled from the FAA.

## Application Deployment

The  application can be deployed in a variety of architectures, the most simple is to [deploy each component as a virtual machine](https://github.com/darrylcauldwell/planeSpotters/tree/master/docs/VM-ALL.md).

## Network Communications

One of uses of the Planespotter app can be to demonstrate NSX features like micro-segmentation policies. The the app is build with this in mind and uses quick timeouts to show the impact of firewall rule changes and includes a 'healtcheck' function that reports back communication issues between the 'microservices' of the app.

Here's the Communication Matrix of the component amongst each other and to the external world:

| Component / Source     | Component / Destination       | Dest Port | Notes                               |
|:-----------------------|:------------------------------|:----------|:------------------------------------|
| Ext. Clients / Browser | Planespotter Frontend         | TCP/80    |                                     |
| Ext. Clients / Browser | www.airport-data.com          | TCP/80    | Display Aircraft Thumbnail picture  |
| Planespotter Frontend  | Planespotter API/APP          | TCP/80    | The listening port is configurable  |
| Planespotter API/APP   | Planespotter MySQL	         | TCP/3306  | 									   |
| Planespotter API/APP   | Planespotter Redis	         | TCP/6379  | 									   |
| Planespotter API/APP   | www.airport-data.com          | TCP/80    | Find Aircraft Thumbnail pictures    |
| Planespotter API/APP   | public-api.adsbexchange.com   | TCP/443   | Retrieves latest Aircraft position  |
| ADSB-Sync       		 | www.airport-data.com          | TCP/443   | Retr. Acft. Airbone stat. in poll   |
| ADSB-Sync       		 | www.airport-data.com          | TCP/32030 | Retr. Acft. Airbone stat. in stream |
| ADSB-Sync       		 | Planespotter Redis            | TCP/6379  | 	

<img src="https://github.com/darrylcauldwell/planeSpotters/blob/master/docs/pics/planespotter-comms.png">

## Acknowledgments

This was forked from the [original Planespotter app](https://github.com/yfauser/planespotter) developed by Yves Fauser.

## License

Copyright © 2018 Yves Fauser. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.