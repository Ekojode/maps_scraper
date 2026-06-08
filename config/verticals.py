HOME_SERVICES = [
    "plumber", "roofer", "HVAC contractor", "electrician", "tree service",
    "pest control", "concrete contractor", "water damage restoration",
    "pool service", "garage door company", "moving company",
    "landscaping company", "fence company", "deck builder", "tile contractor",
    "flooring company", "painting contractor", "general contractor",
    "custom home builder", "home remodeling company",
    "bathroom remodeling company", "kitchen remodeling company",
    "window replacement company", "siding contractor", "gutter company",
    "foundation repair contractor", "basement waterproofing contractor",
    "septic tank service", "water well drilling", "well pump service",
    "house leveling service", "solar panel installer", "masonry contractor",
    "demolition company", "asphalt paving company", "welding service",
    "commercial roofing contractor", "junk removal company",
    "estate cleanout service", "commercial cleaning service",
    "janitorial service", "security system installer", "elevator service",
    "heavy equipment rental", "self storage facility",
    "custom closet builder", "garage organization company",
]

HEALTHCARE = [
    "dentist", "orthodontist", "oral surgeon", "cosmetic dentist",
    "chiropractor", "physical therapist", "podiatrist", "dermatologist",
    "med spa", "plastic surgeon", "lasik eye surgery", "lasik surgeon",
    "cryotherapy center", "longevity clinic", "medical weight loss clinic",
    "fertility clinic", "IVF clinic", "concierge medicine", "family doctor",
    "urgent care", "addiction treatment center", "drug rehab", "psychiatrist",
    "mental health clinic", "audiologist", "hearing aid center",
    "audiology clinic", "assisted living facility", "memory care facility",
    "nursing home", "home health care agency", "senior care agency",
    "veterinary hospital", "emergency vet clinic",
]

LEGAL = [
    "car accident lawyer", "personal injury lawyer",
    "medical malpractice lawyer", "family lawyer", "divorce lawyer",
    "criminal defense lawyer", "estate planning lawyer",
    "immigration lawyer", "real estate lawyer", "business lawyer",
    "corporate law firm", "employment lawyer", "labor lawyer",
    "tax attorney", "tax resolution service", "bankruptcy lawyer",
    "civil litigation lawyer", "bail bonds service", "private investigator",
    "digital forensics service",
]

FINANCIAL = [
    "financial advisor", "insurance agent", "mortgage broker",
    "tax accountant", "CPA", "bookkeeper", "wealth management",
    "retirement planning", "credit repair", "hard money lender",
    "private money lender",
]

AUTOMOTIVE = [
    "luxury auto repair", "exotic car repair", "auto body shop",
    "collision repair", "transmission repair", "transmission shop",
    "diesel truck repair", "fleet maintenance", "auto detailing",
    "ceramic coating", "car wrapping service", "window tinting shop",
    "used car dealership", "RV dealership", "RV repair", "boat dealership",
    "marine mechanic", "towing service", "impound service",
    "flight school", "pilot training",
]

B2B = [
    "commercial real estate broker", "property management company",
    "architecture firm", "civil engineering firm", "interior design firm",
    "event planning company", "catering company", "private security service",
    "copier leasing company", "office equipment supplier",
    "IT support company", "managed service provider",
    "HVAC supply wholesaler", "plumbing supply wholesaler",
]

EDUCATION = [
    "private school", "college prep academy", "CDL training school",
    "truck driving school", "heavy equipment training school",
    "real estate investing seminar",
]

LUXURY = [
    "yacht charter", "boat charter", "wedding venue", "event venue",
    "boutique hotel", "bed and breakfast", "fine dining restaurant",
    "steakhouse", "private jet charter", "luxury pet boarding",
    "pet resort", "golf course", "country club",
]

VERTICALS = (
    HOME_SERVICES + HEALTHCARE + LEGAL + FINANCIAL +
    AUTOMOTIVE + B2B + EDUCATION + LUXURY
)

VERTICAL_CATEGORY = {}
for v in HOME_SERVICES:
    VERTICAL_CATEGORY[v] = "Home Services & Heavy Industrial"
for v in HEALTHCARE:
    VERTICAL_CATEGORY[v] = "Healthcare, Medical & Care"
for v in LEGAL:
    VERTICAL_CATEGORY[v] = "Legal & Investigative"
for v in FINANCIAL:
    VERTICAL_CATEGORY[v] = "Financial"
for v in AUTOMOTIVE:
    VERTICAL_CATEGORY[v] = "Automotive, Marine & Aviation"
for v in B2B:
    VERTICAL_CATEGORY[v] = "B2B, Commercial & Real Estate"
for v in EDUCATION:
    VERTICAL_CATEGORY[v] = "Education & Specialized Training"
for v in LUXURY:
    VERTICAL_CATEGORY[v] = "Luxury Lifestyle, Leisure & Hospitality"


if __name__ == "__main__":
    print(f"Total verticals: {len(VERTICALS)}")
    print(f"  Home Services & Heavy Industrial:      {len(HOME_SERVICES)}")
    print(f"  Healthcare, Medical & Care:            {len(HEALTHCARE)}")
    print(f"  Legal & Investigative:                 {len(LEGAL)}")
    print(f"  Financial:                             {len(FINANCIAL)}")
    print(f"  Automotive, Marine & Aviation:         {len(AUTOMOTIVE)}")
    print(f"  B2B, Commercial & Real Estate:         {len(B2B)}")
    print(f"  Education & Specialized Training:      {len(EDUCATION)}")
    print(f"  Luxury Lifestyle, Leisure & Hospitality: {len(LUXURY)}")
    print(f"\nCategory check: '{VERTICALS[0]}' → {VERTICAL_CATEGORY[VERTICALS[0]]}")
