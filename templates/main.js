// +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class Main {
    constructor(div, zoomDefault, gauge) {

        const self = this; // mmm ...

        this.isWindowActive = true;
        this.vessel = {};
        this.baseLatLng = [1.236104, 103.835729];

        this.gauge = gauge;
        this.map = L.map(div);
        this.map.on('load', function (e) {
            console.log(this);
            // M.show();
        });
        this.map.setView(this.baseLatLng, zoomDefault);
        console.log(this.map.getBounds())
        this.map.on('click', function (e) {
            // this.panTo(e.latlng);  // Wao!
            console.log('latlng = ' + e.latlng);
            console.log(Object.keys(self.vessel).length); // never forget!
        });
        this.map.on('zoomend', function (e) {
            // console.log(this);
            console.log('Zoom = ' + self.map.getZoom())
        });
        this.map.on('moveend', function (e) {
            // console.log(this);
            // console.log('map was pan to ' + self.map.getCenter())
        });

        this.tileLayer = L.tileLayer.grayscale('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
        });
        this.tileLayer.on('load', function (e) {
            // console.log(e);
        });
        this.tileLayer.addTo(this.map);

        this.lockOn = 0;
        this.jingle = new Audio('../static/MP3/se_maoudamashii_system49.mp3');
    }

    setProfeel(mmsi, profeel, debug = true) {
        if (mmsi in this.vessel) {

        } else {
            this.vessel[mmsi] = new Vessel(this, mmsi);
            if (debug) {
                console.log('=== found ' + mmsi + ' = ' + profeel.name);
            }
        }
        const target = this.vessel[mmsi];
        if (target.P === false) {
            target.setProfeel(profeel);
            target.marker.addTo(this.map);
        }
        // this.vessel[mmsi].marker.bounce()
        // console.log('+++ ' + mmsi + ' = ' + profeel.name);
    }

    setLocation(mmsi, location) {
        if (mmsi in this.vessel) {

        } else {
            this.vessel[mmsi] = new Vessel(this, mmsi);
            // console.log('+++ Found ' + mmsi);
        }
        this.vessel[mmsi].setLocation(location);
        // console.log('+++ ' + mmsi + ' = ' + profeel.name);
    }
// ---------------------------------------------------------------------
    move(mmsi, location) { //console.log(location)
        if (mmsi in this.vessel) {
            const target = this.vessel[mmsi];

            const top = target.marker.getLatLng()
            // console.log(location)
            const d = this.distance(top['lat'], top['lng'], location['lat'], location['lon']);
            if (d) { //console.log(d)
                const status = parseInt(location['status']);
                if (status === 1 || status === 2 || status === 3) {
                    target.marker.setIcon(target.stopicon);
                } else {
                    target.marker.setIcon(target.icon);
                }
                // console.log('>>> ' + mmsi + ' was moved ' + d)
                target.counter++;
                const duration = 1000;
                if (target.P) {
                    // const duration = target.profeel.AISclass === 'A' ? 500 : 1000;
                    const opacity = location['sog'] > 0.5 ? 1.0 : 0.5;
                    target.marker.setOpacity(opacity);
                }
                target.marker.setRotationAngle(location['hdg']);
                target.marker.setOpacity(1.0);
                const lonlat = L.latLng(location['lat'], location['lon']);
                if (this.isWindowActive) {
                    target.marker.moveTo(lonlat, duration);
                } else {
                    target.marker.setLatLng(lonlat);
                }
                // if (this.lockOn && mmsi === this.lockOn) {
                //     this.jingle.play();
                //     console.log('Chasing ' + mmsi + ' ' + location.sog);
                //     // console.log(self);
                //     this.map.panTo([location.lat, location.lon]);
                //     this.gauge.set(location.sog);
                // }
            } else {
                if (isNaN(d)) {
                    console.log(mmsi + ' NaN at ' + top + ' and ' + location)
                }
                // console.log('distance = ' + d)
            }
        } else {
            this.setLocation(mmsi, location);
        }
    }

// ---------------------------------------------------------------------
    expire(mmsi) {
        if (mmsi in this.vessel) {
            const target = this.vessel[mmsi];
            this.map.removeLayer(target.marker);
            const name = target.P ? target.profeel.name : 'unkown';
            delete this.vessel[mmsi];
            console.log('--- ' + name + ' was retired');
        }
    }

    isInside(location) {
        const bound = this.map.getBounds();
        return (
            location.lat > bound._southWest.lat &&
            location.lat < bound._northEast.lat &&
            location.lon > bound._southWest.lng &&
            location.lon < bound._northEast.lng
        )
    }

    distance(lat1, lng1, lat2, lng2) {
        if (lat1 !== lat2 || lng1 !== lng2) {
            // console.log(lat1, lng1, lat2, lng2)
            lat1 *= Math.PI / 180;
            lng1 *= Math.PI / 180;
            lat2 *= Math.PI / 180;
            lng2 *= Math.PI / 180;
            return 6371 * Math.acos(Math.cos(lat1) * Math.cos(lat2) * Math.cos(lng2 - lng1) + Math.sin(lat1) * Math.sin(lat2));
        } else {
            console.log('*** zero distance');
            return 0;
        }
    }
}

