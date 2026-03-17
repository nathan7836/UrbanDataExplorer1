/**
 * Donnees de sante de proximite par arrondissement de Paris
 * Sources: OpenData Paris (defibrillateurs), FINESS, Assurance Maladie
 *
 * Indicateurs:
 * - pharmacies: nombre total de pharmacies
 * - pharmacies_garde: pharmacies de garde (nuit/dimanche)
 * - defibrillateurs: DAE accessibles au public
 * - dentistes: cabinets dentaires
 * - centres_sante: centres de sante municipaux
 * - medecins_generalistes: medecins generalistes
 * - urgences_proximite: temps moyen vers urgences (minutes)
 * - hopitaux_cliniques: hopitaux et cliniques dans l'arrondissement
 */

const SANTE_DATA = {
    "metadata": {
        "source": "OpenData Paris, FINESS, Assurance Maladie",
        "annee": 2024,
        "derniere_maj": "2024-12-01",
        "notes": "Donnees agreges par arrondissement"
    },
    "sante_by_arrondissement": {
        "1": {
            "pharmacies": 28,
            "pharmacies_garde": 3,
            "defibrillateurs": 42,
            "dentistes": 35,
            "centres_sante": 1,
            "medecins_generalistes": 45,
            "urgences_proximite": 8,
            "hopitaux_cliniques": 1,
            "population": 16266,
            "superficie_km2": 1.83
        },
        "2": {
            "pharmacies": 22,
            "pharmacies_garde": 2,
            "defibrillateurs": 28,
            "dentistes": 25,
            "centres_sante": 1,
            "medecins_generalistes": 32,
            "urgences_proximite": 10,
            "hopitaux_cliniques": 0,
            "population": 21331,
            "superficie_km2": 0.99
        },
        "3": {
            "pharmacies": 25,
            "pharmacies_garde": 2,
            "defibrillateurs": 31,
            "dentistes": 28,
            "centres_sante": 1,
            "medecins_generalistes": 38,
            "urgences_proximite": 9,
            "hopitaux_cliniques": 0,
            "population": 34115,
            "superficie_km2": 1.17
        },
        "4": {
            "pharmacies": 30,
            "pharmacies_garde": 3,
            "defibrillateurs": 48,
            "dentistes": 32,
            "centres_sante": 1,
            "medecins_generalistes": 42,
            "urgences_proximite": 5,
            "hopitaux_cliniques": 2,
            "population": 28088,
            "superficie_km2": 1.60
        },
        "5": {
            "pharmacies": 45,
            "pharmacies_garde": 4,
            "defibrillateurs": 52,
            "dentistes": 55,
            "centres_sante": 2,
            "medecins_generalistes": 68,
            "urgences_proximite": 4,
            "hopitaux_cliniques": 3,
            "population": 58850,
            "superficie_km2": 2.54
        },
        "6": {
            "pharmacies": 52,
            "pharmacies_garde": 4,
            "defibrillateurs": 45,
            "dentistes": 62,
            "centres_sante": 1,
            "medecins_generalistes": 85,
            "urgences_proximite": 6,
            "hopitaux_cliniques": 2,
            "population": 41100,
            "superficie_km2": 2.15
        },
        "7": {
            "pharmacies": 48,
            "pharmacies_garde": 4,
            "defibrillateurs": 55,
            "dentistes": 58,
            "centres_sante": 1,
            "medecins_generalistes": 78,
            "urgences_proximite": 7,
            "hopitaux_cliniques": 2,
            "population": 51367,
            "superficie_km2": 4.09
        },
        "8": {
            "pharmacies": 65,
            "pharmacies_garde": 5,
            "defibrillateurs": 72,
            "dentistes": 85,
            "centres_sante": 1,
            "medecins_generalistes": 120,
            "urgences_proximite": 8,
            "hopitaux_cliniques": 3,
            "population": 36808,
            "superficie_km2": 3.88
        },
        "9": {
            "pharmacies": 55,
            "pharmacies_garde": 4,
            "defibrillateurs": 48,
            "dentistes": 52,
            "centres_sante": 2,
            "medecins_generalistes": 65,
            "urgences_proximite": 9,
            "hopitaux_cliniques": 1,
            "population": 59555,
            "superficie_km2": 2.18
        },
        "10": {
            "pharmacies": 58,
            "pharmacies_garde": 5,
            "defibrillateurs": 52,
            "dentistes": 48,
            "centres_sante": 3,
            "medecins_generalistes": 55,
            "urgences_proximite": 6,
            "hopitaux_cliniques": 2,
            "population": 90372,
            "superficie_km2": 2.89
        },
        "11": {
            "pharmacies": 72,
            "pharmacies_garde": 6,
            "defibrillateurs": 58,
            "dentistes": 65,
            "centres_sante": 3,
            "medecins_generalistes": 72,
            "urgences_proximite": 7,
            "hopitaux_cliniques": 1,
            "population": 146643,
            "superficie_km2": 3.67
        },
        "12": {
            "pharmacies": 85,
            "pharmacies_garde": 6,
            "defibrillateurs": 68,
            "dentistes": 72,
            "centres_sante": 4,
            "medecins_generalistes": 82,
            "urgences_proximite": 8,
            "hopitaux_cliniques": 3,
            "population": 142583,
            "superficie_km2": 16.32
        },
        "13": {
            "pharmacies": 95,
            "pharmacies_garde": 7,
            "defibrillateurs": 75,
            "dentistes": 78,
            "centres_sante": 5,
            "medecins_generalistes": 88,
            "urgences_proximite": 5,
            "hopitaux_cliniques": 4,
            "population": 181552,
            "superficie_km2": 7.15
        },
        "14": {
            "pharmacies": 78,
            "pharmacies_garde": 6,
            "defibrillateurs": 62,
            "dentistes": 68,
            "centres_sante": 4,
            "medecins_generalistes": 75,
            "urgences_proximite": 6,
            "hopitaux_cliniques": 3,
            "population": 135964,
            "superficie_km2": 5.64
        },
        "15": {
            "pharmacies": 115,
            "pharmacies_garde": 8,
            "defibrillateurs": 88,
            "dentistes": 95,
            "centres_sante": 5,
            "medecins_generalistes": 125,
            "urgences_proximite": 7,
            "hopitaux_cliniques": 4,
            "population": 233392,
            "superficie_km2": 8.48
        },
        "16": {
            "pharmacies": 95,
            "pharmacies_garde": 7,
            "defibrillateurs": 78,
            "dentistes": 88,
            "centres_sante": 3,
            "medecins_generalistes": 135,
            "urgences_proximite": 9,
            "hopitaux_cliniques": 3,
            "population": 166361,
            "superficie_km2": 16.31
        },
        "17": {
            "pharmacies": 88,
            "pharmacies_garde": 6,
            "defibrillateurs": 65,
            "dentistes": 75,
            "centres_sante": 4,
            "medecins_generalistes": 95,
            "urgences_proximite": 8,
            "hopitaux_cliniques": 2,
            "population": 167288,
            "superficie_km2": 5.67
        },
        "18": {
            "pharmacies": 92,
            "pharmacies_garde": 7,
            "defibrillateurs": 58,
            "dentistes": 62,
            "centres_sante": 5,
            "medecins_generalistes": 68,
            "urgences_proximite": 6,
            "hopitaux_cliniques": 3,
            "population": 195233,
            "superficie_km2": 6.01
        },
        "19": {
            "pharmacies": 78,
            "pharmacies_garde": 6,
            "defibrillateurs": 52,
            "dentistes": 55,
            "centres_sante": 4,
            "medecins_generalistes": 58,
            "urgences_proximite": 7,
            "hopitaux_cliniques": 2,
            "population": 187015,
            "superficie_km2": 6.79
        },
        "20": {
            "pharmacies": 88,
            "pharmacies_garde": 7,
            "defibrillateurs": 55,
            "dentistes": 58,
            "centres_sante": 5,
            "medecins_generalistes": 62,
            "urgences_proximite": 8,
            "hopitaux_cliniques": 2,
            "population": 195814,
            "superficie_km2": 5.98
        }
    }
};

/**
 * Calcule le score de sante de proximite pour un arrondissement
 * Score de 0 a 100 base sur l'accessibilite aux services de sante
 */
function calculateScoreSanteProximite(arrData) {
    if (!arrData) return null;

    const pop = arrData.population || 50000;
    const surface = arrData.superficie_km2 || 3;

    // Ratios pour 10 000 habitants
    const ratioPharmacies = (arrData.pharmacies / pop) * 10000;
    const ratioDentistes = (arrData.dentistes / pop) * 10000;
    const ratioMedecins = (arrData.medecins_generalistes / pop) * 10000;
    const ratioDefib = (arrData.defibrillateurs / pop) * 10000;

    // Densite par km2
    const densitePharmacies = arrData.pharmacies / surface;
    const densiteCentresSante = arrData.centres_sante / surface;

    // Score urgences (inverse - plus proche = mieux)
    const scoreUrgences = Math.max(0, 100 - (arrData.urgences_proximite * 8));

    // Score composite (pondere)
    const scores = {
        pharmacies: Math.min(100, ratioPharmacies * 15),        // ~6-7 pharmacies/10k hab = 100
        dentistes: Math.min(100, ratioDentistes * 12),          // ~8 dentistes/10k hab = 100
        medecins: Math.min(100, ratioMedecins * 8),             // ~12 medecins/10k hab = 100
        defibrillateurs: Math.min(100, ratioDefib * 20),        // ~5 DAE/10k hab = 100
        urgences: scoreUrgences,
        centres: Math.min(100, densiteCentresSante * 50),       // ~2 centres/km2 = 100
        hopitaux: Math.min(100, arrData.hopitaux_cliniques * 25) // 4 hopitaux = 100
    };

    // Ponderations
    const weights = {
        pharmacies: 0.20,
        dentistes: 0.15,
        medecins: 0.20,
        defibrillateurs: 0.10,
        urgences: 0.20,
        centres: 0.10,
        hopitaux: 0.05
    };

    let scoreTotal = 0;
    for (const [key, weight] of Object.entries(weights)) {
        scoreTotal += scores[key] * weight;
    }

    return {
        score: Math.round(scoreTotal),
        details: scores,
        ratios: {
            pharmacies_10k: ratioPharmacies.toFixed(1),
            dentistes_10k: ratioDentistes.toFixed(1),
            medecins_10k: ratioMedecins.toFixed(1),
            defibrillateurs_10k: ratioDefib.toFixed(1)
        }
    };
}

/**
 * Retourne le niveau d'accessibilite sante
 */
function getNiveauSante(score) {
    if (score >= 80) return { niveau: "Excellent", classe: "sante-excellent" };
    if (score >= 65) return { niveau: "Tres bon", classe: "sante-tres-bon" };
    if (score >= 50) return { niveau: "Bon", classe: "sante-bon" };
    if (score >= 35) return { niveau: "Moyen", classe: "sante-moyen" };
    return { niveau: "A ameliorer", classe: "sante-faible" };
}
