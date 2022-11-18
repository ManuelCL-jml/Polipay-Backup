from rest_framework import serializers

from apps.users.models import persona, cuenta, tcuenta, tarjeta
from apps.transaction.models import transferencia
from apps.users.management import Code_card
from polipaynewConfig.inntec import *
from MANAGEMENT.EncryptDecrypt.encdec_nip_cvc_token4dig import encdec_nip_cvc_token4dig
from apps.productos.models import producto
from apps.languages.models import Cat_languages
from MANAGEMENT.Language.LanguageUnregisteredUser import LanguageUnregisteredUser
from MANAGEMENT.Language.LanguageRegisteredUser import LanguageRegisteredUser
from MANAGEMENT.EndPoint.EndPointInfo import get_info
from MANAGEMENT.Logs.SystemLog import RegisterSystemLog


# ----------------------------------------------------------------------------------------------------

class serializerCuentaWalletIn(serializers.Serializer):
	email = serializers.CharField()
	tarjeta = serializers.IntegerField()
	nip = serializers.CharField(allow_null=True, allow_blank=True)
	cvc = serializers.CharField(allow_blank=True)
	fechaexp = serializers.DateField(allow_null=False, default=None)
	alias = serializers.CharField(allow_null=False)
	product	= serializers.IntegerField()
	lang	= serializers.CharField()

	def validate_product(self, value):
		queryExisteProduct = producto.objects.filter(id=value).exists()
		if not queryExisteProduct:
			msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg003BE")
			#raise serializers.ValidationError({"status": "Debe proporcionar un producto correcto."})
			raise serializers.ValidationError({"status": msg})
		return value

	def validate_lang(self, value):
		#queryExisteIdioma = Cat_languages.objects.filter(id=value).exists()
		#if not queryExisteIdioma:
		#	raise serializers.ValidationError({"status": "Debe proporcionar un idioma correcto."})
		return value

	def validate(self, attrs):
		instance = persona.objects.get(email=attrs['email'])
		query = tarjeta.objects.filter(tarjeta=attrs['tarjeta'])
		if len(query) != 0:
			acount = tarjeta.objects.get(tarjeta=attrs['tarjeta'])
			if acount.cuenta_id == None:
				return attrs
			else:
				instance.delete()
				msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg004BE")
				#raise serializers.ValidationError({"status": "Tarjeta ya ha sido asiganada"})
				raise serializers.ValidationError({"status": msg})
		else:
			instance.delete()
			msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg005BE")
			#raise serializers.ValidationError({"status": "Tarjeta ya ha sido registrada"})
			raise serializers.ValidationError({"status": msg})

	def save(self, instance):
		try:
			#cuentaclave = "XXXXXXXXXXXXXXXX" + str(Code_card(2))

			# (ChrAvaBus - mie08.12.2021 17:08) Se agrega funcionalidad por cliente de Movimiento Zapopan (TMP)
			ARRAY_TMP_TARJETAS = [
				5129121205297004,
				5129121205360000,
				5129121205365009,
				5129121206062001,
				5129121209973006,
				5129121209995009,
				5129121210004007,
				5129121210039003,
				5129121218266004,
				5129121218353000,
				5129121218363009,
				5129121218392008,
				5129121218606001,
				5129121218714003,
				5129121218755006,
				5129121218772001,
				5129121259351004,
				5129121259361003,
				5129121259375003,
				5129121259392008,
				5129121259404001,
				5129121259415007,
				5129121259434008,
				5129121259464005,
				5129121259486008,
				5129121259497005,
				5129121259523008,
				5129121259543006,
				5129121259574001,
				5129121259615002,
				5129121259667003,
				5129121259688009,
				5129121259739000,
				5129121259741006,
				5129121259758000,
				5129121259763000,
				5129121259801008,
				5129121259803004,
				5129121259804002,
				5129121259808003,
				5129121259856002,
				5129121259869005,
				5129121259876000,
				5129121259976008,
				5129121260008007,
				5129121260016000,
				5129121260030001,
				5129121260033005,
				5129121260050009,
				5129121260053003,
				5129121260095004,
				5129121260097000,
				5129121260103006,
				5129121260108005,
				5129121260113005,
				5129121260121008,
				5129121260129001,
				5129121260156004,
				5129121260189005,
				5129121260283006,
				5129121260290001,
				5129121260323000,
				5129121260326003,
				5129121260341002,
				5129121260357008,
				5129121260383004,
				5129121260387005,
				5129121260394001,
				5129121260418008,
				5129121260425003,
				5129121260433007,
				5129121260449003,
				5129121260492003,
				5129121260618003,
				5129121260625008,
				5129121260664007,
				5129121260668008,
				5129121260674006,
				5129121260703003,
				5129121261025000,
				5129121261063001,
				5129121261101009,
				5129121261103005,
				5129121261115009,
				5129121261138001,
				5129121261174006,
				5129121261223001,
				5129121261239007,
				5129121261268006,
				5129121261296007,
				5129121261315005,
				5129121261337009,
				5129121261354004,
				5129121261379001,
				5129121261390008,
				5129121261424005,
				5129121261447006,
				5129121261489008,
				5129121261500002,
				5129121261519002,
				5129121261540008,
				5129121261547003,
				5129121261561004,
				5129121261596000,
				5129121261600000,
				5129121261609001,
				5129121261631005,
				5129121261633001,
				5129121261999006,
				5129121262020000,
				5129121262070005,
				5129121262073009,
				5129121262096000,
				5129121262112005,
				5129121262122004,
				5129121262147001,
				5129121262175002,
				5129121262177008,
				5129121262180002,
				5129121262219008,
				5129121262228009,
				5129121262243008,
				5129121262244006,
				5129121262266009,
				5129121262291007,
				5129121262303000,
				5129121262367005,
				5129121262401002,
				5129121262405003,
				5129121262428005,
				5129121262452005,
				5129121262463002,
				5129121262493009,
				5129121262508004,
				5129121262549008,
				5129121262577009,
				5129121262593006,
				5129121262598005,
				5129121262616005,
				5129121262622003,
				5129121262626004,
				5129121262631004,
				5129121262643009,
				5129121262724007,
				5129121262726002,
				5129121262784001,
				5129121262790008,
				5129121262801003,
				5129121262813008,
				5129121262825002,
				5129121262842007,
				5129121262847006,
				5129121262864001,
				5129121262892002,
				5129121262918005,
				5129121262930000,
				5129121262935009,
				5129121262953002,
				5129121262962003,
				5129121262987000,
				5129121263005000,
				5129121263018003,
				5129121263019001,
				5129121263024001,
				5129121263037003,
				5129121263046004,
				5129121263251000,
				5129121263277005,
				5129121263414004,
				5129121263482001,
				5129121263491002,
				5129121263579004,
				5129121263708009,
				5129121263723008,
				5129121263735002,
				5129121263736000,
				5129121263756008,
				5129121263779000,
				5129121263803008,
				5129121271957002,
				5129121271981002,
				5129121271984006,
				5129121272023002,
				5129121272056002,
				5129121272060004,
				5129121272075002,
				5129121272078006,
				5129121272080002,
				5129121272081000,
				5129121272100008,
				5129121272132001,
				5129121272152009,
				5129121272184002,
				5129121272202002,
				5129121272228007,
				5129121272258004,
				5129121272270009,
				5129121272286005,
				5129121272323006,
				5129121272356006,
				5129121272360008,
				5129121272366005,
				5129121272424002,
				5129121272469007,
				5129121272487009,
				5129121272617001,
				5129121272674002,
				5129121272688002,
				5129121272695007,
				5129121272722009,
				5129121272768002,
				5129121272783001,
				5129121272785006,
				5129121272824003,
				5129121272868000,
				5129121273001007,
				5129121273012004,
				5129121273028000,
				5129121273041003,
				5129121273053008,
				5129121273062009,
				5129121273065002,
				5129121273087006,
				5129121273120005,
				5129121273133008,
				5129121273163005,
				5129121273166008,
				5129121273208008,
				5129121273305002
			]

			OBJ_JSON_TMP = {
				5129121205297004: {"clabe": "646180171801800900"},
				5129121205360000: {"clabe": "646180171801800913"},
				5129121205365009: {"clabe": "646180171801800926"},
				5129121206062001: {"clabe": "646180171801800939"},
				5129121209973006: {"clabe": "646180171801800942"},
				5129121209995009: {"clabe": "646180171801800955"},
				5129121210004007: {"clabe": "646180171801800968"},
				5129121210039003: {"clabe": "646180171801800971"},
				5129121218266004: {"clabe": "646180171801800984"},
				5129121218353000: {"clabe": "646180171801800997"},
				5129121218363009: {"clabe": "646180171801801006"},
				5129121218392008: {"clabe": "646180171801801019"},
				5129121218606001: {"clabe": "646180171801801022"},
				5129121218714003: {"clabe": "646180171801801035"},
				5129121218755006: {"clabe": "646180171801801048"},
				5129121218772001: {"clabe": "646180171801801051"},
				5129121259351004: {"clabe": "646180171801801064"},
				5129121259361003: {"clabe": "646180171801801077"},
				5129121259375003: {"clabe": "646180171801801080"},
				5129121259392008: {"clabe": "646180171801801093"},
				5129121259404001: {"clabe": "646180171801801103"},
				5129121259415007: {"clabe": "646180171801801116"},
				5129121259434008: {"clabe": "646180171801801129"},
				5129121259464005: {"clabe": "646180171801801132"},
				5129121259486008: {"clabe": "646180171801801145"},
				5129121259497005: {"clabe": "646180171801801158"},
				5129121259523008: {"clabe": "646180171801801161"},
				5129121259543006: {"clabe": "646180171801801174"},
				5129121259574001: {"clabe": "646180171801801187"},
				5129121259615002: {"clabe": "646180171801801190"},
				5129121259667003: {"clabe": "646180171801801200"},
				5129121259688009: {"clabe": "646180171801801213"},
				5129121259739000: {"clabe": "646180171801801226"},
				5129121259741006: {"clabe": "646180171801801239"},
				5129121259758000: {"clabe": "646180171801801242"},
				5129121259763000: {"clabe": "646180171801801255"},
				5129121259801008: {"clabe": "646180171801801268"},
				5129121259803004: {"clabe": "646180171801801271"},
				5129121259804002: {"clabe": "646180171801801284"},
				5129121259808003: {"clabe": "646180171801801297"},
				5129121259856002: {"clabe": "646180171801801307"},
				5129121259869005: {"clabe": "646180171801801310"},
				5129121259876000: {"clabe": "646180171801801323"},
				5129121259976008: {"clabe": "646180171801801336"},
				5129121260008007: {"clabe": "646180171801801349"},
				5129121260016000: {"clabe": "646180171801801352"},
				5129121260030001: {"clabe": "646180171801801365"},
				5129121260033005: {"clabe": "646180171801801378"},
				5129121260050009: {"clabe": "646180171801801381"},
				5129121260053003: {"clabe": "646180171801801394"},
				5129121260095004: {"clabe": "646180171801801404"},
				5129121260097000: {"clabe": "646180171801801417"},
				5129121260103006: {"clabe": "646180171801801420"},
				5129121260108005: {"clabe": "646180171801801433"},
				5129121260113005: {"clabe": "646180171801801446"},
				5129121260121008: {"clabe": "646180171801801459"},
				5129121260129001: {"clabe": "646180171801801462"},
				5129121260156004: {"clabe": "646180171801801475"},
				5129121260189005: {"clabe": "646180171801801488"},
				5129121260283006: {"clabe": "646180171801801491"},
				5129121260290001: {"clabe": "646180171801801501"},
				5129121260323000: {"clabe": "646180171801801514"},
				5129121260326003: {"clabe": "646180171801801527"},
				5129121260341002: {"clabe": "646180171801801530"},
				5129121260357008: {"clabe": "646180171801801543"},
				5129121260383004: {"clabe": "646180171801801556"},
				5129121260387005: {"clabe": "646180171801801569"},
				5129121260394001: {"clabe": "646180171801801572"},
				5129121260418008: {"clabe": "646180171801801585"},
				5129121260425003: {"clabe": "646180171801801598"},
				5129121260433007: {"clabe": "646180171801801608"},
				5129121260449003: {"clabe": "646180171801801611"},
				5129121260492003: {"clabe": "646180171801801624"},
				5129121260618003: {"clabe": "646180171801801637"},
				5129121260625008: {"clabe": "646180171801801640"},
				5129121260664007: {"clabe": "646180171801801653"},
				5129121260668008: {"clabe": "646180171801801666"},
				5129121260674006: {"clabe": "646180171801801679"},
				5129121260703003: {"clabe": "646180171801801682"},
				5129121261025000: {"clabe": "646180171801801695"},
				5129121261063001: {"clabe": "646180171801801705"},
				5129121261101009: {"clabe": "646180171801801718"},
				5129121261103005: {"clabe": "646180171801801721"},
				5129121261115009: {"clabe": "646180171801801734"},
				5129121261138001: {"clabe": "646180171801801747"},
				5129121261174006: {"clabe": "646180171801801750"},
				5129121261223001: {"clabe": "646180171801801763"},
				5129121261239007: {"clabe": "646180171801801776"},
				5129121261268006: {"clabe": "646180171801801789"},
				5129121261296007: {"clabe": "646180171801801792"},
				5129121261315005: {"clabe": "646180171801801802"},
				5129121261337009: {"clabe": "646180171801801815"},
				5129121261354004: {"clabe": "646180171801801828"},
				5129121261379001: {"clabe": "646180171801801831"},
				5129121261390008: {"clabe": "646180171801801844"},
				5129121261424005: {"clabe": "646180171801801857"},
				5129121261447006: {"clabe": "646180171801801860"},
				5129121261489008: {"clabe": "646180171801801873"},
				5129121261500002: {"clabe": "646180171801801886"},
				5129121261519002: {"clabe": "646180171801801899"},
				5129121261540008: {"clabe": "646180171801801909"},
				5129121261547003: {"clabe": "646180171801801912"},
				5129121261561004: {"clabe": "646180171801801925"},
				5129121261596000: {"clabe": "646180171801801938"},
				5129121261600000: {"clabe": "646180171801801941"},
				5129121261609001: {"clabe": "646180171801801954"},
				5129121261631005: {"clabe": "646180171801801967"},
				5129121261633001: {"clabe": "646180171801801970"},
				5129121261999006: {"clabe": "646180171801801983"},
				5129121262020000: {"clabe": "646180171801801996"},
				5129121262070005: {"clabe": "646180171801802005"},
				5129121262073009: {"clabe": "646180171801802018"},
				5129121262096000: {"clabe": "646180171801802021"},
				5129121262112005: {"clabe": "646180171801802034"},
				5129121262122004: {"clabe": "646180171801802047"},
				5129121262147001: {"clabe": "646180171801802050"},
				5129121262175002: {"clabe": "646180171801802063"},
				5129121262177008: {"clabe": "646180171801802076"},
				5129121262180002: {"clabe": "646180171801802089"},
				5129121262219008: {"clabe": "646180171801802092"},
				5129121262228009: {"clabe": "646180171801802102"},
				5129121262243008: {"clabe": "646180171801802115"},
				5129121262244006: {"clabe": "646180171801802128"},
				5129121262266009: {"clabe": "646180171801802131"},
				5129121262291007: {"clabe": "646180171801802144"},
				5129121262303000: {"clabe": "646180171801802157"},
				5129121262367005: {"clabe": "646180171801802160"},
				5129121262401002: {"clabe": "646180171801802173"},
				5129121262405003: {"clabe": "646180171801802186"},
				5129121262428005: {"clabe": "646180171801802199"},
				5129121262452005: {"clabe": "646180171801802209"},
				5129121262463002: {"clabe": "646180171801802212"},
				5129121262493009: {"clabe": "646180171801802225"},
				5129121262508004: {"clabe": "646180171801802238"},
				5129121262549008: {"clabe": "646180171801802241"},
				5129121262577009: {"clabe": "646180171801802254"},
				5129121262593006: {"clabe": "646180171801802267"},
				5129121262598005: {"clabe": "646180171801802270"},
				5129121262616005: {"clabe": "646180171801802283"},
				5129121262622003: {"clabe": "646180171801802296"},
				5129121262626004: {"clabe": "646180171801802306"},
				5129121262631004: {"clabe": "646180171801802319"},
				5129121262643009: {"clabe": "646180171801802322"},
				5129121262724007: {"clabe": "646180171801802335"},
				5129121262726002: {"clabe": "646180171801802348"},
				5129121262784001: {"clabe": "646180171801802351"},
				5129121262790008: {"clabe": "646180171801802364"},
				5129121262801003: {"clabe": "646180171801802377"},
				5129121262813008: {"clabe": "646180171801802380"},
				5129121262825002: {"clabe": "646180171801802393"},
				5129121262842007: {"clabe": "646180171801802403"},
				5129121262847006: {"clabe": "646180171801802416"},
				5129121262864001: {"clabe": "646180171801802429"},
				5129121262892002: {"clabe": "646180171801802432"},
				5129121262918005: {"clabe": "646180171801802445"},
				5129121262930000: {"clabe": "646180171801802458"},
				5129121262935009: {"clabe": "646180171801802461"},
				5129121262953002: {"clabe": "646180171801802474"},
				5129121262962003: {"clabe": "646180171801802487"},
				5129121262987000: {"clabe": "646180171801802490"},
				5129121263005000: {"clabe": "646180171801802500"},
				5129121263018003: {"clabe": "646180171801802513"},
				5129121263019001: {"clabe": "646180171801802526"},
				5129121263024001: {"clabe": "646180171801802539"},
				5129121263037003: {"clabe": "646180171801802542"},
				5129121263046004: {"clabe": "646180171801802555"},
				5129121263251000: {"clabe": "646180171801802568"},
				5129121263277005: {"clabe": "646180171801802571"},
				5129121263414004: {"clabe": "646180171801802584"},
				5129121263482001: {"clabe": "646180171801802597"},
				5129121263491002: {"clabe": "646180171801802607"},
				5129121263579004: {"clabe": "646180171801802610"},
				5129121263708009: {"clabe": "646180171801802623"},
				5129121263723008: {"clabe": "646180171801802636"},
				5129121263735002: {"clabe": "646180171801802649"},
				5129121263736000: {"clabe": "646180171801802652"},
				5129121263756008: {"clabe": "646180171801802665"},
				5129121263779000: {"clabe": "646180171801802678"},
				5129121263803008: {"clabe": "646180171801802681"},
				5129121271957002: {"clabe": "646180171801802694"},
				5129121271981002: {"clabe": "646180171801802704"},
				5129121271984006: {"clabe": "646180171801802717"},
				5129121272023002: {"clabe": "646180171801802720"},
				5129121272056002: {"clabe": "646180171801802733"},
				5129121272060004: {"clabe": "646180171801802746"},
				5129121272075002: {"clabe": "646180171801802759"},
				5129121272078006: {"clabe": "646180171801802762"},
				5129121272080002: {"clabe": "646180171801802775"},
				5129121272081000: {"clabe": "646180171801802788"},
				5129121272100008: {"clabe": "646180171801802791"},
				5129121272132001: {"clabe": "646180171801802801"},
				5129121272152009: {"clabe": "646180171801802814"},
				5129121272184002: {"clabe": "646180171801802827"},
				5129121272202002: {"clabe": "646180171801802830"},
				5129121272228007: {"clabe": "646180171801802843"},
				5129121272258004: {"clabe": "646180171801802856"},
				5129121272270009: {"clabe": "646180171801802869"},
				5129121272286005: {"clabe": "646180171801802872"},
				5129121272323006: {"clabe": "646180171801802885"},
				5129121272356006: {"clabe": "646180171801802898"},
				5129121272360008: {"clabe": "646180171801802908"},
				5129121272366005: {"clabe": "646180171801802911"},
				5129121272424002: {"clabe": "646180171801802924"},
				5129121272469007: {"clabe": "646180171801802937"},
				5129121272487009: {"clabe": "646180171801802940"},
				5129121272617001: {"clabe": "646180171801802953"},
				5129121272674002: {"clabe": "646180171801802966"},
				5129121272688002: {"clabe": "646180171801802979"},
				5129121272695007: {"clabe": "646180171801802982"},
				5129121272722009: {"clabe": "646180171801802995"},
				5129121272768002: {"clabe": "646180171801803004"},
				5129121272783001: {"clabe": "646180171801803017"},
				5129121272785006: {"clabe": "646180171801803020"},
				5129121272824003: {"clabe": "646180171801803033"},
				5129121272868000: {"clabe": "646180171801803046"},
				5129121273001007: {"clabe": "646180171801803059"},
				5129121273012004: {"clabe": "646180171801803062"},
				5129121273028000: {"clabe": "646180171801803075"},
				5129121273041003: {"clabe": "646180171801803088"},
				5129121273053008: {"clabe": "646180171801803091"},
				5129121273062009: {"clabe": "646180171801803101"},
				5129121273065002: {"clabe": "646180171801803114"},
				5129121273087006: {"clabe": "646180171801803127"},
				5129121273120005: {"clabe": "646180171801803130"},
				5129121273133008: {"clabe": "646180171801803143"},
				5129121273163005: {"clabe": "646180171801803156"},
				5129121273166008: {"clabe": "646180171801803169"},
				5129121273208008: {"clabe": "646180171801803172"},
				5129121273305002: {"clabe": "646180171801803185"}
			}

			cuentaclave = ""

			if int(self.validated_data.get("tarjeta")) in ARRAY_TMP_TARJETAS:
				cuentaclave = OBJ_JSON_TMP[int(self.data.get("tarjeta"))]["clabe"]
			else:
				query_set = cuenta.objects.filter(cuenta__contains="XXXXX").values("id", "cuenta").latest("id")
				numActual = query_set["cuenta"][5:]
				numConsecutivo = int(numActual) + 1
				operacionModdulo = int(numConsecutivo) % 10
				cuentaConsecutivo = int(numConsecutivo) / 10000
				cuentaConsecutivo = str(cuentaConsecutivo).replace(".", "")
				if operacionModdulo == 0:
					cuentaclave = "XXXXXXXXXXXX" + str(cuentaConsecutivo) + "00"
				else:
					cuentaclave = "XXXXXXXXXXXX" + str(cuentaConsecutivo) + "0"

			cuentaPerson		= cuentaclave[7:17]
			instanceAccount 	= cuenta.objects.create(
				cuenta=cuentaPerson,
				monto=0,
				is_active=True,
				persona_cuenta_id=instance.id,
				cuentaclave=cuentaclave,
				rel_cuenta_prod_id=self.validated_data.get("product")
			)
			insatnceTarjeta = tarjeta.objects.get(tarjeta=self.validated_data.get('tarjeta'))
			insatnceTarjeta.cuenta_id = instanceAccount.id
			insatnceTarjeta.alias = self.validated_data.get('alias')
			# Cifrado
			objJson				= encdec_nip_cvc_token4dig("1", "BE", self.validated_data.get('cvc'))
			insatnceTarjeta.cvc	= objJson["data"]
			# Cifrado
			objJson				= encdec_nip_cvc_token4dig("1", "BE", self.validated_data.get('nip'))
			insatnceTarjeta.nip	= objJson["data"]
			insatnceTarjeta.fechaexp = self.validated_data.get('fechaexp')
			insatnceTarjeta.save()
			return instanceAccount
		except Exception as inst:
			instance.delete()
			msg = LanguageUnregisteredUser(self.initial_data.get("lang"), "Reg006BE")
			msg	= msg.replace("<e>", str(inst))
			#raise serializers.ValidationError({"Status": [inst]})
			raise serializers.ValidationError({"Status": msg})


class serializerCuentaWalletTajetaIn(serializers.Serializer):
	email = serializers.CharField()
	tarjeta = serializers.IntegerField()
	cvc = serializers.CharField(allow_blank=True)
	fechaexp = serializers.DateField(allow_null=False, default=None)
	alias = serializers.CharField(allow_null=False)
	nip = serializers.CharField(allow_null=True, allow_blank=True)

	def validate(self, attrs):
		instance = persona.objects.get(email=attrs['email'])
		query = tarjeta.objects.filter(tarjeta=attrs['tarjeta'])
		if len(query) != 0:
			acount = tarjeta.objects.get(tarjeta=attrs['tarjeta'])
			if acount.cuenta_id == None:
				return attrs
			else:
				idPersona	= get_id(campo="email", valorStr=str(self.initial_data.get("email")))
				msg			= LanguageRegisteredUser(idPersona, "Das004BE")
				raise serializers.ValidationError({"status": msg})
				#raise serializers.ValidationError({"status": "Tarjeta ya ha sido asiganada"})
		else:
			idPersona	= get_id(campo="email", valorStr=str(self.initial_data.get("email")))
			msg			= LanguageRegisteredUser(idPersona, "Das005BE")
			raise serializers.ValidationError({"status": msg})
			#raise serializers.ValidationError({"status": "Tarjeta no existe"})

	def save(self, instance):
		try:
			insatnceTarjeta = tarjeta.objects.get(tarjeta=self.validated_data.get('tarjeta'))
			insatnceTarjeta.cuenta_id = instance.id
			insatnceTarjeta.alias = self.validated_data.get('alias')
			# Cifrado
			objJson				= encdec_nip_cvc_token4dig("1", "BE", self.validated_data.get('cvc'))
			insatnceTarjeta.cvc = objJson["data"]
			insatnceTarjeta.fechaexp = self.validated_data.get('fechaexp')
			insatnceTarjeta.nip = self.validated_data.get('nip')
			insatnceTarjeta.save()
			return insatnceTarjeta
		except Exception as inst:
			counts = cuenta.objects.filter(persona_cuenta=instance)
			if len(counts) == 0:
				instance.delete()
			idPersona	= get_id(campo="email", valorStr=str(self.initial_data.get("email")))
			msg			= LanguageRegisteredUser(idPersona, "Das006BE")
			msg			= msg.replace("<e>", inst)
			raise serializers.ValidationError({"status": [msg]})
			#raise serializers.ValidationError({"Status": [inst]})


# ----------------------------------------------------------------------------------------------------


class serializerPutUserWalletChangeStatusIn(serializers.Serializer):
	status = serializers.BooleanField()


class serializerCuentaOutUser(serializers.Serializer):
	id = serializers.ReadOnlyField()
	cuenta = serializers.CharField()
	fecha_creacion = serializers.DateTimeField()
	monto = serializers.FloatField()
	is_active = serializers.BooleanField()
	cuentaclave = serializers.CharField()
	tarjetas = serializers.SerializerMethodField()

	def get_tarjetas(self, obj: tarjetas):
		query = tarjeta.objects.filter(cuenta_id=obj.id, was_eliminated=False)
		return serializerTrajetasOut(query, many=True).data


class serializerTrajetasOut(serializers.Serializer):
	id = serializers.ReadOnlyField()
	tarjeta = serializers.CharField()
	nip = serializers.SerializerMethodField()
	is_active = serializers.SerializerMethodField()
	tipo_cuenta = serializers.SerializerMethodField()
	monto = serializers.SerializerMethodField()
	status = serializers.SerializerMethodField()
	TarjetaId = serializers.IntegerField()
	ClaveEmpleado = serializers.CharField()
	NumeroCuenta = serializers.CharField()
	cvc = serializers.SerializerMethodField()
	fechaexp = serializers.DateField()
	alias = serializers.CharField()

	def get_tipo_cuenta(self, obj: tipo_cuenta):
		query = tcuenta.objects.get(id=obj.tipo_cuenta_id)
		return query.nTCuenta

	def get_monto(self, obj: monto):
		monto = get_Saldo(obj.tarjeta)
		obj.monto = monto
		obj.save()
		return obj.monto
	def get_status(self, obj: status):
		statusQ = get_status(obj.tarjeta)
		obj.status = statusQ
		obj.save()
		return obj.status
	def get_is_active(self, obj: is_active):
		active = False
		statusQ = get_status(obj.tarjeta)
		if statusQ == '00':
			obj.is_active = True
			obj.save()
		return obj.is_active
	def get_cvc(self, obj: cvc):
		# Descifrado
		objJson	= encdec_nip_cvc_token4dig("2", "BE", obj.cvc)
		return objJson["data"]
	def get_nip(self, obj: nip):
		# Descifrado
		objJson	= encdec_nip_cvc_token4dig("2", "BE", obj.nip)
		return objJson["data"]


class serializerAcountIn(serializers.Serializer):
	ProductoId = serializers.IntegerField()
	ClaveEmpleado = serializers.CharField()
	TarjetaId = serializers.IntegerField()
	NumeroTarjeta = serializers.CharField()
	NumeroCuenta = serializers.CharField()

	def save(self, validated_data):
		try:
			query = tarjeta.objects.get(tarjeta=validated_data.get('NumeroTarjeta'))
			# print('existe')
			# active = False
			# if status == '00':
			# 	active = True
			# tarjetaInstance = query[0]
			# tarjetaInstance.monto = saldo
			# tarjetaInstance.status = status
			# tarjetaInstance.is_active = active
			# tarjetaInstance.save()
			return None
		except:
			status = get_status(validated_data.get('NumeroTarjeta'))
			saldo = get_Saldo(validated_data.get('NumeroTarjeta'))
			active = False
			if status == '00':
				active = True
			instance = tarjeta.objects.create(
				tarjeta=validated_data.get('NumeroTarjeta'),
				is_active=active,
				tipo_cuenta_id=1,
				monto=saldo,
				status=status,
				TarjetaId=validated_data.get('TarjetaId'),
				ClaveEmpleado=validated_data.get('ClaveEmpleado'),
				NumeroCuenta=validated_data.get('NumeroCuenta')
			)
			return instance.tarjeta

class serializerEditAlias(serializers.Serializer):
	alias		= serializers.CharField()
	cvc		= serializers.CharField()
	fechaexp	= serializers.DateField()

	def alias_rename(self,instance):
		instance.alias = self.validated_data.get("alias",instance.alias)
		instance.save()
		return True
	def cvc_rename(self,instance):
		# Cifrado
		objJson			= encdec_nip_cvc_token4dig("1", "BE", self.validated_data.get("cvc",instance.cvc))
		instance.cvc	= objJson["data"]
		instance.save()
		return True
	def fechaexp_rename(self,instance):
		instance.fechaexp = self.validated_data.get("fechaexp",instance.fechaexp)
		instance.save()
		return True

