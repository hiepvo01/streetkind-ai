/** Mirrors ClientFormSchema defaults — keep in sync with backend client schema. */
export const createBlankClient = () => ({
    firstName: '',
    lastName: '',
    gender: '',
    ageGroup: '',
    email: '',
    contactNumber: '',
    suburb: '',
    alone: false,
    intoxicationSigns: { speech: false, balance: false, coordination: false, behaviour: false, notVisible: false },
    drugUseSigns: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
    offensiveConduct: { offensiveBehaviour: false, offensiveLanguage: false, obstruction: false, publicDrinking: false, notVisible: false },
    selfHarmSigns: { visibleSigns: false, disclosed: false, notVisible: false },
    suicidalSigns: { ideationObserved: false, ideationDisclosed: false, attemptObserved: false, attemptDisclosed: false, notVisible: false },
    sexualAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
    physicalAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
    domesticViolence: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
    reconnection: { telephone: false, person: false, socialNetwork: false },
    directions: { venue: false, accommodation: false, other: false },
    transportInformation: { bus: false, train: false, taxi: false, uber: false, other: false },
    escortedTo: { accommodation: false, transport: false, friends: false, other: false },
    safeSpace: { escortedTo: false, soberedUp: false },
    basicAid: { vomitBag: false, water: false, footwear: false, lollipop: false },
    additionalAid: { firstAid: false, mentalHealthAid: false },
    emergencyServicesCalled: { ambulanceServiceCalled: false, policeServiceCalled: false, fireServiceCalled: false },
    physicalAssaultRisk: 0,
    sexualAssaultRisk: 0,
    clientConsciousness: 0,
    clientValuablesVisibility: 0,
    clientLostProperty: 0,
    injury: { roadRelated: false, other: false },
    clientServiceReferrals: {
        alcoholDrugInfoService: false, beyondBlue: false, childProtectionServices: false,
        dvLine: false, hospital: false, lifeline: false, link2home: false,
        salvosStreetLevel: false, streetbeatBus: false, traffickingSlaveryAFP: false,
    },
    serviceInformation: { contactedService: false, infoProvided: false },
    otherSupport: { welfareCheck: false, homelessSupport: false },
});

const zeroGenderAge = () => ({
    lessThan18: 0,
    from18to25: 0,
    from26to39: 0,
    over40: 0,
});

export function createEmptyIncidentFormData(defaultSite = '') {
    return {
        incident: {
            teamLeaderName: '',
            site: defaultSite || '',
            location: { address: '', latitude: null, longitude: null },
            encounteredBy: {},
            otherServicesInvolved: {},
            quickNote: '',
            incidentDescription: '',
            incidentOutcome: '',
            majorIncident: false,
        },
        clients: [createBlankClient()],
    };
}

export function createEmptySafeBaseFormData(defaultSite = '') {
    return {
        site: defaultSite || '',
        startTime: Date.now(),
        male: zeroGenderAge(),
        female: zeroGenderAge(),
        nonBinary: zeroGenderAge(),
        assistanceRendered: {
            directions: 0,
            bus: 0,
            train: 0,
            taxi: 0,
            deviceCharge: 0,
            familyReconnect: 0,
        },
    };
}
