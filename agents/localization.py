from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BilingualTemplate:
    text: str
    english: str

    def render(self, **values: object) -> tuple[str, str]:
        return self.text.format(**values), self.english.format(**values)


@dataclass(frozen=True)
class NegotiationLanguage:
    quote_request: BilingualTemplate
    opening_offer: BilingualTemplate
    agent_counter: BilingualTemplate
    buyer_counter: BilingualTemplate
    buyer_accept: BilingualTemplate
    agent_close: BilingualTemplate
    buyer_ack: BilingualTemplate
    below_floor_close: BilingualTemplate


LANGUAGES: dict[str, NegotiationLanguage] = {
    "hi-IN": NegotiationLanguage(
        quote_request=BilingualTemplate(
            "नमस्ते {name} जी। {location} के किसान के पास {quantity} क्विंटल {crop} है, ग्रेड {grade}। आप खेत से उठाकर क्या भाव दे सकते हैं?",
            "Hello {name}. A farmer in {location} has {quantity} quintals of grade {grade} {crop_en}. What farm-gate price can you offer?",
        ),
        opening_offer=BilingualTemplate(
            "माल बताए गए ग्रेड का हुआ तो मेरी शुरुआती बोली ₹{price} प्रति क्विंटल है। {payment_clause} {pickup_clause}",
            "If the produce matches the stated grade, my opening offer is ₹{price} per quintal. {payment_clause_en} {pickup_clause_en}",
        ),
        agent_counter=BilingualTemplate(
            "आज के आसपास के मंडी भाव और मात्रा देखते हुए किसान ₹{price} प्रति क्विंटल मांग रहे हैं। क्या आप इसके करीब आ सकते हैं?",
            "Considering nearby mandi prices and the quantity, the farmer is asking ₹{price} per quintal. Can you move closer to that?",
        ),
        buyer_counter=BilingualTemplate(
            "इतना संभव नहीं है। मैं बोली बढ़ाकर ₹{price} प्रति क्विंटल कर सकता हूँ; इससे ऊपर मार्जिन नहीं बचेगा।",
            "That is not possible. I can increase the offer to ₹{price} per quintal; above that I would have no margin.",
        ),
        buyer_accept=BilingualTemplate(
            "ठीक है, बताए गए ग्रेड और वजन की पुष्टि पर ₹{price} प्रति क्विंटल मान सकता हूँ।",
            "All right. Subject to confirmation of grade and weight, I can agree to ₹{price} per quintal.",
        ),
        agent_close=BilingualTemplate(
            "मैं ₹{price} की इस बोली को अस्थायी कोट के रूप में दर्ज कर रहा हूँ। अंतिम फैसला किसान की पुष्टि के बाद होगा।",
            "I am recording this ₹{price} offer as a provisional quote. It becomes final only after the farmer confirms.",
        ),
        buyer_ack=BilingualTemplate(
            "ठीक है। भाव {valid_hours} घंटे तक मान्य रहेगा; माल देखकर अंतिम वजन तय होगा।",
            "Understood. The quote remains valid for {valid_hours} hours; final weight will be confirmed after inspection.",
        ),
        below_floor_close=BilingualTemplate(
            "आपकी अंतिम बोली ₹{price} किसान की न्यूनतम सीमा ₹{floor} से कम है। मैं इसे तुलना के लिए दर्ज कर रहा हूँ, स्वीकार नहीं कर रहा।",
            "Your final offer of ₹{price} is below the farmer's ₹{floor} floor. I will record it for comparison but not accept it.",
        ),
    ),
    "mr-IN": NegotiationLanguage(
        quote_request=BilingualTemplate(
            "नमस्कार {name}जी. {location} येथील शेतकऱ्याकडे ग्रेड {grade} चा {quantity} क्विंटल {crop} आहे. शेतातून उचल करून तुम्ही किती भाव देऊ शकता?",
            "Hello {name}. A farmer in {location} has {quantity} quintals of grade {grade} {crop_en}. What farm-gate price can you offer with pickup?",
        ),
        opening_offer=BilingualTemplate(
            "माल सांगितलेल्या दर्जाचा असेल तर माझी सुरुवातीची बोली ₹{price} प्रति क्विंटल. {payment_clause} {pickup_clause}",
            "If the produce matches the stated grade, my opening offer is ₹{price} per quintal. {payment_clause_en} {pickup_clause_en}",
        ),
        agent_counter=BilingualTemplate(
            "आजचा जवळच्या बाजाराचा भाव आणि एकूण माल पाहता शेतकऱ्याची अपेक्षा ₹{price} प्रति क्विंटल आहे. तुम्ही या भावाजवळ येऊ शकता का?",
            "Considering today's nearby market price and the lot size, the farmer expects ₹{price} per quintal. Can you move closer to it?",
        ),
        buyer_counter=BilingualTemplate(
            "तो भाव मला परवडणार नाही. मी ₹{price} प्रति क्विंटलपर्यंत वाढवू शकतो; त्यापुढे माझा खर्च निघणार नाही.",
            "That price does not work for me. I can increase to ₹{price} per quintal; beyond that my costs will not be covered.",
        ),
        buyer_accept=BilingualTemplate(
            "ठीक आहे. दर्जा आणि वजन तपासल्यानंतर ₹{price} प्रति क्विंटल मान्य आहे.",
            "All right. Subject to grade and weight inspection, ₹{price} per quintal is acceptable.",
        ),
        agent_close=BilingualTemplate(
            "₹{price} ची ही बोली मी तात्पुरती नोंदवत आहे. शेतकऱ्याने होकार दिल्यानंतरच व्यवहार निश्चित होईल.",
            "I am recording this ₹{price} offer provisionally. The deal is confirmed only after the farmer approves.",
        ),
        buyer_ack=BilingualTemplate(
            "चालेल. हा भाव {valid_hours} तासांसाठी आहे; माल पाहून अंतिम वजन ठरवू.",
            "Agreed. This quote is valid for {valid_hours} hours; final weight will be decided after inspection.",
        ),
        below_floor_close=BilingualTemplate(
            "तुमची ₹{price} ची अंतिम बोली शेतकऱ्याच्या ₹{floor} किमान भावापेक्षा कमी आहे. तुलना करण्यासाठी नोंद करतो, पण स्वीकारत नाही.",
            "Your final offer of ₹{price} is below the farmer's ₹{floor} minimum. I will record it for comparison but not accept it.",
        ),
    ),
    "pa-IN": NegotiationLanguage(
        quote_request=BilingualTemplate(
            "ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name} ਜੀ। {location} ਦੇ ਕਿਸਾਨ ਕੋਲ ਗ੍ਰੇਡ {grade} ਦੀ {quantity} ਕੁਇੰਟਲ {crop} ਹੈ। ਖੇਤ ਤੋਂ ਚੁੱਕ ਕੇ ਤੁਸੀਂ ਕੀ ਭਾਅ ਦੇ ਸਕਦੇ ਹੋ?",
            "Hello {name}. A farmer in {location} has {quantity} quintals of grade {grade} {crop_en}. What farm-gate price can you offer with pickup?",
        ),
        opening_offer=BilingualTemplate(
            "ਜੇ ਮਾਲ ਦੱਸੇ ਹੋਏ ਗ੍ਰੇਡ ਦਾ ਹੋਇਆ ਤਾਂ ਮੇਰੀ ਪਹਿਲੀ ਪੇਸ਼ਕਸ਼ ₹{price} ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਹੈ। {payment_clause} {pickup_clause}",
            "If the produce matches the stated grade, my opening offer is ₹{price} per quintal. {payment_clause_en} {pickup_clause_en}",
        ),
        agent_counter=BilingualTemplate(
            "ਨੇੜਲੀ ਮੰਡੀ ਦੇ ਅੱਜ ਦੇ ਭਾਅ ਅਤੇ ਮਾਤਰਾ ਮੁਤਾਬਕ ਕਿਸਾਨ ₹{price} ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਮੰਗਦਾ ਹੈ। ਕੀ ਤੁਸੀਂ ਇਸ ਦੇ ਨੇੜੇ ਆ ਸਕਦੇ ਹੋ?",
            "Based on today's nearby mandi prices and the quantity, the farmer asks ₹{price} per quintal. Can you move closer?",
        ),
        buyer_counter=BilingualTemplate(
            "ਉਹ ਭਾਅ ਮੇਰੇ ਲਈ ਔਖਾ ਹੈ। ਮੈਂ ₹{price} ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਤੱਕ ਵਧਾ ਸਕਦਾ ਹਾਂ; ਇਸ ਤੋਂ ਉੱਪਰ ਖਰਚਾ ਨਹੀਂ ਨਿਕਲੇਗਾ।",
            "That price is difficult for me. I can increase to ₹{price} per quintal; above that my costs will not be covered.",
        ),
        buyer_accept=BilingualTemplate(
            "ਠੀਕ ਹੈ। ਗ੍ਰੇਡ ਅਤੇ ਵਜ਼ਨ ਦੀ ਜਾਂਚ ਤੋਂ ਬਾਅਦ ₹{price} ਪ੍ਰਤੀ ਕੁਇੰਟਲ ਮਨਜ਼ੂਰ ਹੈ।",
            "All right. Subject to checking grade and weight, ₹{price} per quintal is acceptable.",
        ),
        agent_close=BilingualTemplate(
            "ਮੈਂ ₹{price} ਦੀ ਪੇਸ਼ਕਸ਼ ਅਸਥਾਈ ਕੋਟ ਵਜੋਂ ਦਰਜ ਕਰ ਰਿਹਾ ਹਾਂ। ਕਿਸਾਨ ਦੀ ਮਨਜ਼ੂਰੀ ਤੋਂ ਬਾਅਦ ਹੀ ਸੌਦਾ ਪੱਕਾ ਹੋਵੇਗਾ।",
            "I am recording the ₹{price} offer as a provisional quote. The deal becomes final only after the farmer approves.",
        ),
        buyer_ack=BilingualTemplate(
            "ਠੀਕ ਹੈ। ਇਹ ਭਾਅ {valid_hours} ਘੰਟਿਆਂ ਲਈ ਰਹੇਗਾ; ਮਾਲ ਵੇਖ ਕੇ ਆਖਰੀ ਵਜ਼ਨ ਤੈਅ ਕਰਾਂਗੇ।",
            "Understood. This quote remains valid for {valid_hours} hours; final weight will be set after inspection.",
        ),
        below_floor_close=BilingualTemplate(
            "ਤੁਹਾਡੀ ₹{price} ਦੀ ਆਖਰੀ ਪੇਸ਼ਕਸ਼ ਕਿਸਾਨ ਦੇ ₹{floor} ਘੱਟੋ-ਘੱਟ ਭਾਅ ਤੋਂ ਹੇਠਾਂ ਹੈ। ਮੈਂ ਤੁਲਨਾ ਲਈ ਦਰਜ ਕਰਾਂਗਾ, ਮਨਜ਼ੂਰ ਨਹੀਂ ਕਰਾਂਗਾ।",
            "Your final offer of ₹{price} is below the farmer's ₹{floor} floor. I will record it for comparison but not accept it.",
        ),
    ),
    "ta-IN": NegotiationLanguage(
        quote_request=BilingualTemplate(
            "வணக்கம் {name}. {location} பகுதியில் உள்ள விவசாயியிடம் தரம் {grade} கொண்ட {quantity} குவிண்டால் {crop} உள்ளது. வயலில் இருந்து எடுத்துச் செல்ல நீங்கள் என்ன விலை தர முடியும்?",
            "Hello {name}. A farmer in {location} has {quantity} quintals of grade {grade} {crop_en}. What farm-gate price can you offer with pickup?",
        ),
        opening_offer=BilingualTemplate(
            "சொன்ன தரத்தில் சரக்கு இருந்தால், எனது முதல் விலை குவிண்டாலுக்கு ₹{price}. {payment_clause} {pickup_clause}",
            "If the produce matches the stated grade, my opening price is ₹{price} per quintal. {payment_clause_en} {pickup_clause_en}",
        ),
        agent_counter=BilingualTemplate(
            "அருகிலுள்ள சந்தையின் இன்றைய விலையும் அளவும் பார்த்தால், விவசாயி குவிண்டாலுக்கு ₹{price} எதிர்பார்க்கிறார். அந்த விலைக்கு அருகில் வர முடியுமா?",
            "Considering today's nearby market price and quantity, the farmer expects ₹{price} per quintal. Can you move closer?",
        ),
        buyer_counter=BilingualTemplate(
            "அந்த விலை எனக்கு கட்டுப்படாது. குவிண்டாலுக்கு ₹{price} வரை உயர்த்த முடியும்; அதற்கு மேல் செலவு ஈடாகாது.",
            "That price does not work for me. I can increase to ₹{price} per quintal; above that my costs will not be covered.",
        ),
        buyer_accept=BilingualTemplate(
            "சரி. தரமும் எடையும் சரிபார்த்த பிறகு குவிண்டாலுக்கு ₹{price} ஒப்புக்கொள்கிறேன்.",
            "All right. Subject to checking grade and weight, I agree to ₹{price} per quintal.",
        ),
        agent_close=BilingualTemplate(
            "₹{price} விலையை தற்காலிக மேற்கோளாக பதிவு செய்கிறேன். விவசாயி ஒப்புக்கொண்ட பிறகே விற்பனை உறுதியாகும்.",
            "I am recording ₹{price} as a provisional quote. The sale is confirmed only after the farmer approves.",
        ),
        buyer_ack=BilingualTemplate(
            "சரி. இந்த விலை {valid_hours} மணி நேரம் செல்லுபடியாகும்; சரக்கைப் பார்த்த பிறகு இறுதி எடையை உறுதி செய்வோம்.",
            "Understood. This quote is valid for {valid_hours} hours; final weight will be confirmed after inspection.",
        ),
        below_floor_close=BilingualTemplate(
            "உங்கள் இறுதி விலை ₹{price}, விவசாயியின் குறைந்தபட்ச விலை ₹{floor}-க்கு கீழே உள்ளது. ஒப்பீட்டுக்காக பதிவு செய்கிறேன்; ஏற்கவில்லை.",
            "Your final price of ₹{price} is below the farmer's ₹{floor} floor. I will record it for comparison but not accept it.",
        ),
    ),
    "te-IN": NegotiationLanguage(
        quote_request=BilingualTemplate(
            "నమస్కారం {name} గారు. {location} రైతు దగ్గర గ్రేడ్ {grade} {crop} {quantity} క్వింటాళ్లు ఉంది. పొలం దగ్గరే తీసుకెళ్తే మీరు ఎంత ధర ఇవ్వగలరు?",
            "Hello {name}. A farmer in {location} has {quantity} quintals of grade {grade} {crop_en}. What farm-gate price can you offer with pickup?",
        ),
        opening_offer=BilingualTemplate(
            "చెప్పిన గ్రేడ్‌లో సరుకు ఉంటే నా మొదటి ధర క్వింటాల్‌కు ₹{price}. {payment_clause} {pickup_clause}",
            "If the produce matches the stated grade, my opening price is ₹{price} per quintal. {payment_clause_en} {pickup_clause_en}",
        ),
        agent_counter=BilingualTemplate(
            "దగ్గర మార్కెట్‌లో ఈరోజు ధర, మొత్తం పరిమాణం చూసి రైతు క్వింటాల్‌కు ₹{price} అడుగుతున్నారు. ఆ ధరకు దగ్గరగా రాగలరా?",
            "Considering today's nearby market price and the quantity, the farmer asks ₹{price} per quintal. Can you move closer?",
        ),
        buyer_counter=BilingualTemplate(
            "ఆ ధర నాకు కుదరదు. క్వింటాల్‌కు ₹{price} వరకు పెంచగలను; అంతకంటే ఎక్కువైతే ఖర్చు సరిపోదు.",
            "That price does not work for me. I can increase to ₹{price} per quintal; above that my costs will not be covered.",
        ),
        buyer_accept=BilingualTemplate(
            "సరే. గ్రేడ్, బరువు తనిఖీ చేసిన తర్వాత క్వింటాల్‌కు ₹{price} అంగీకరిస్తాను.",
            "All right. Subject to grade and weight inspection, I agree to ₹{price} per quintal.",
        ),
        agent_close=BilingualTemplate(
            "₹{price} ధరను తాత్కాలిక కోట్‌గా నమోదు చేస్తున్నాను. రైతు అంగీకరించిన తర్వాతే ఒప్పందం ఖరారు అవుతుంది.",
            "I am recording ₹{price} as a provisional quote. The agreement is final only after the farmer approves.",
        ),
        buyer_ack=BilingualTemplate(
            "సరే. ఈ ధర {valid_hours} గంటల వరకు ఉంటుంది; సరుకు చూసిన తర్వాత తుది బరువు ఖరారు చేద్దాం.",
            "Understood. This quote is valid for {valid_hours} hours; final weight will be confirmed after inspection.",
        ),
        below_floor_close=BilingualTemplate(
            "మీ తుది ధర ₹{price}, రైతు కనీస ధర ₹{floor} కంటే తక్కువ. పోలిక కోసం నమోదు చేస్తాను, కానీ అంగీకరించను.",
            "Your final price of ₹{price} is below the farmer's ₹{floor} floor. I will record it for comparison but not accept it.",
        ),
    ),
}


def negotiation_language(language_code: str) -> NegotiationLanguage:
    return LANGUAGES.get(language_code, LANGUAGES["hi-IN"])
