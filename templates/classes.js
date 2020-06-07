// -------------------------------------------------------------------------------------------------
class Profeel {
    constructor(name, callsign, imo, AISclass, shipType) {
        this.name = name;
        this.callsign = callsign;
        this.imo = parseInt(imo);
        this.AISclass = AISclass;
        this.shipType = shipType;
    }
}

class Location {
    constructor(lon, lat, sog, hdg, sv) {
        this.lon = parseFloat(lon);
        this.lat = parseFloat(lat);
        this.sog = parseFloat(sog);
        this.hdg = parseInt(hdg);
        this.sv = sv;
    }
}

// -------------------------------------------------------------------------------------------------
class Vessel {
    constructor(main, mmsi) {

        const self = this; // mmm ...

        this.main = main;
        this.mmsi = mmsi;
        this.at = new Date();
        this.P = false;
        this.L = false;
        this.counter = 0;

        this.icon = L.icon({
            iconUrl: '../static/imgs/ufo.png',
            iconSize: [16, 16],
        });

        this.marker = L.Marker.movingMarker([[0, 0]], [], {
            icon: this.icon,
            rotationAngle: 0,
            bounceOnAdd: false,
            bounceOnAddOptions: {
                height: 128,
                duration: 1000,
                loop: 1,
            },
        });
        this.marker.setOpacity(0.25);
        this.stopicon = L.icon({
            iconUrl: '../static/imgs/anchor.png',
        });
        this.marker.on('click', function (e) {
            console.log(this.profeel);
            self.main.lockOn = parseInt(self.mmsi);
            console.log(self.main);
            // speechSynthesis.cancel();
            this.talker.text = this.profeel.name //+ ' ' + this.profeel.callsign;
            speechSynthesis.speak(this.talker);
        })

        this.talker = new SpeechSynthesisUtterance();
        this.talker.lang = 'en-US';
        this.talker.rate = 1.0;
        // this.talker.rate = 0.75;
        this.talker.onend = function (e) {
            speechSynthesis.cancel();
            console.log('### elapsed ' + e.elapsedTime / 1000);
        }

        this.marker.name = 'unkown'
        this.marker.talker = this.talker
    }

    setProfeel(profeel) { //console.log(profeel)
        this.profeel = profeel;
        this.marker.profeel = profeel
        if (this.P === false) {
            this.P = true;

            this.marker.bindTooltip(this.profeel.name);
            // this.marker.bindPopup(this.profeel.name);

            let img = '../static/imgs/kaniS.png';
            if (profeel.AISclass !== 'A') {
                img = '../static/imgs/ant.png';
            } else {
                if ((profeel.shipType / 10) === 8) {
                    img = '../static/imgs/oil.png';
                } else if ((profeel.shipType / 10) === 7) {
                    img = '../static/imgs/kameS.png';
                } else if ((profeel.shipType / 10) === 5) {
                    img = '../static/imgs/rocket.png';
                } else if ((profeel.shipType / 10) === 3) {
                    img = '../static/imgs/55.png';
                } else if ((profeel.shipType / 10) === 6) {
                    img = '../static/imgs/smile.png';
                }
            }
            this.icon = L.icon({iconUrl: img}); // console.log(this.icon)
            // this.marker.setIcon(this.icon);
        }
    }

    setLocation(location) {
        this.location = location;
        this.counter++;
        if (this.L === false) {
            this.L = true;
        }
    }
}


