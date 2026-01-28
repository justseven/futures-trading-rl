#include "CUser.h"

SMCertUser::SMCertUser()
{
	m_smcert = getConfig("config", "SMCert");
	m_brokerid = getConfig("config", "BrokerID");
	m_userid = getConfig("config", "UserID");
	m_password = getConfig("config", "Password");
	m_PIN = getConfig("config", "PIN");
	m_SMFrontAddr = getConfig("config", "SMFrontAddr");
	m_SMPort = getConfig("config", "SMPort");
	m_SSLFrontAddr = getConfig("config", "SSLFrontAddr");


	/* SDK 错误码 */
	m_map_errormsg[SMCERTSDK_ERR_NONE] = "/* 成功 */";
	m_map_errormsg[SMCERTSDK_ERR_BASE] = "/* 错误码 */";
	m_map_errormsg[SMCERTSDK_ERR_FAILED] = "  /* 失败 */";
	m_map_errormsg[SMCERTSDK_ERR_LOCALRETRY] = "/* 本地主动调用异步接口重试 */";

	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_UNKNOWN] = "/* 内部未知错误 */";
	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_GENKEY] = "/* 产生密钥对失败 */";
	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_DIGEST] = "/* 摘要失败 */";
	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_BASE64] = "/* base64编码失败 */";
	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_RANDOM] = "/* 产生随机数失败 */";
	m_map_errormsg[SMCERTSDK_ERR_INTERNAL_XTSIGN] = "/* 协同签名失败 */";

	m_map_errormsg[SMCERTSDK_ERR_PARAM_NULL] = "/* 空参数 */";
	m_map_errormsg[SMCERTSDK_ERR_PARAM_INVALID] = "  /* 参数非法 */";
	m_map_errormsg[SMCERTSDK_ERR_PARAM_BUFFER_SMALL]="/* 缓冲区太小 */";

	m_map_errormsg[SMCERTSDK_ERR_NETWORK_CONNECT] = "/* 连接出错 */";
	m_map_errormsg[SMCERTSDK_ERR_NETWORK_REQUEST] = "/* 请求错误 */";
	m_map_errormsg[SMCERTSDK_ERR_NETWORK_RESPONSE] = "/* 响应错误 */";

	m_map_errormsg[SMCERTSDK_ERR_STORE_UNKNOWN] = "/* 存储未知错误 */";
	m_map_errormsg[SMCERTSDK_ERR_PIN_INCORRECT] = "/* PIN 不正确 */";
	m_map_errormsg[SMCERTSDK_ERR_PIN_LOCKED] = "/* PIN 已锁定 */";
	m_map_errormsg[SMCERTSDK_ERR_CERT_NOT_EXISTS] = "/* 本地证书不存在 */";
	m_map_errormsg[SMCERTSDK_ERR_CERT_EXPIRED] = "/* 证书过期 */";
	m_map_errormsg[SMCERTSDK_ERR_CERT_OVERLIMIT] = "/* 证书个数超限 */";
	m_map_errormsg[SMCERTSDK_ERR_CERT_INVALID] = "/* 证书无效，以及其他未定义错误 */";
	m_map_errormsg[SMCERTSDK_ERR_USER_PASS] = "/* 错误的用户名或密码 */";
	m_map_errormsg[SMCERTSDK_ERR_PIN_WRONGFORMAT] = "/* PIN码格式不正确 */";

	/* SSL错误码 */
	m_map_errormsg[SMSSLCERT_ERROR_NONE] = "/* 操作成功 */";
	m_map_errormsg[SMSSLCERT_ERROR_SSL] = "/* SSL错误 */";
	m_map_errormsg[SMSSLCERT_ERROR_WANT_READ] = "/* 读阻塞 */";
	m_map_errormsg[SMSSLCERT_ERROR_WANT_WRITE] = "/* 写阻塞 */";
	m_map_errormsg[SMSSLCERT_ERROR_SYSCALL] = "/* 系统中断 */";
	m_map_errormsg[SMSSLCERT_ERROR_ZERO_RETURN] = "/* SSL连接关闭 */";
	m_map_errormsg[SMSSLCERT_ERROR_WANT_CONNECT] = "/* 连接阻塞 */";
	m_map_errormsg[SMSSLCERT_ERROR_WANT_ACCEPT] = "/* 监听阻塞 */";
}

SMCertUser::~SMCertUser()
{

}

void SMCertUser::Ctp_LoadAPI()
{
	//动态加载dll和函数
	if (m_smcert == "smk")
	{
		m_hLib = LoadLibrary(L"smk_certsdk.dll");
	}
	else if (m_smcert == "sms")
	{
		m_hLib = LoadLibrary(L"sms_certsdk.dll");
	}
	else if (m_smcert == "smi")
	{
		m_hLib = LoadLibrary(L"smi_certsdk.dll");
	}
	else
	{
		LOG("Error SMCertSDK...\n");
	}
	if (nullptr == m_hLib)
	{
		LOG("No SMCertSDK API Available...\n");
		exit(-1);
	}

	m_SMCertSDK_Version = (SM_GetVersion)GetProcAddress(m_hLib, "SMCertSDK_GetVersion");
	if (NULL == m_SMCertSDK_Version)
	{
		LOG("Loading SMCertSDK_GetVersion Function failed.\n");
		return;
	}
	m_SMCertSDK_Init = (SM_Init)GetProcAddress(m_hLib, "SMCertSDK_Init");
	if (NULL == m_SMCertSDK_Init)
	{
		LOG("Loading SMCertSDK_Init Function failed.\n");
		return;
	}
	m_SMCertSDK_Clean = (SM_Clean)GetProcAddress(m_hLib, "SMCertSDK_Clean");
	if (NULL == m_SMCertSDK_Clean)
	{
		LOG("Loading SMCertSDK_Clean Function failed.\n");
		return;
	}
	m_SMCertSDK_New = (SM_New)GetProcAddress(m_hLib, "SMCertSDK_New");
	if (NULL == m_SMCertSDK_New)
	{
		LOG("Loading SMCertSDK_New Function failed.\n");
		return;
	}
	m_SMCertSDK_Free = (SM_Free)GetProcAddress(m_hLib, "SMCertSDK_Free");
	if (NULL == m_SMCertSDK_Free)
	{
		LOG("Loading SMCertSDK_Free Function failed.\n");
		return;
	}
	m_SMCertSDK_CertQuery = (SM_CertQuery)GetProcAddress(m_hLib, "SMCertSDK_CertQuery");
	if (NULL == m_SMCertSDK_CertQuery)
	{
		LOG("Loading SMCertSDK_CertQuery Function failed.\n");
		return;
	}
	m_SMCertSDK_CertEnroll = (SM_CertEnroll)GetProcAddress(m_hLib, "SMCertSDK_CertEnroll");
	if (NULL == m_SMCertSDK_CertEnroll)
	{
		LOG("Loading SMCertSDK_CertEnroll Function failed.\n");
		return;
	}
	m_SMCertSDK_CertDelay = (SM_CertDelay)GetProcAddress(m_hLib, "SMCertSDK_CertDelay");
	if (NULL == m_SMCertSDK_CertDelay)
	{
		LOG("Loading SMCertSDK_CertDelay Function failed.\n");
		return;
	}
	m_SMCertSDK_CertRevoke = (SM_CertRevoke)GetProcAddress(m_hLib, "SMCertSDK_CertRevoke");
	if (NULL == m_SMCertSDK_CertRevoke)
	{
		LOG("Loading SMCertSDK_CertRevoke Function failed.\n");
		return;
	}
	m_SMCertSDK_ResetPin = (SM_ResetPin)GetProcAddress(m_hLib, "SMCertSDK_ResetPin");
	if (NULL == m_SMCertSDK_ResetPin)
	{
		LOG("Loading SMCertSDK_ResetPin Function failed.\n");
		return;
	}
}

void SMCertUser::Ctp_SMCertSDK_GetVersion()
{
	LOG("------Current SMCertSDK APIverion : %s, %s-------\n", m_smcert.c_str(), m_SMCertSDK_Version());
}

void SMCertUser::Ctp_SMCertSDK_Init()
{
	int rst = m_SMCertSDK_Init("sdk.log");
	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_Init Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_Init DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_Clean()
{
	int rst = m_SMCertSDK_Clean();
	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_Clean Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_Clean DONE : 0x%X\n, %s", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_New()
{
	m_cert = new SMCertSDK_t;
	m_cfg = new SMCertUserConfig_t;
	memset(m_cfg, 0, sizeof(SMCertUserConfig_t));
	m_cfg->BrokerID = m_brokerid.c_str();
	m_cfg->UserID = m_userid.c_str();
	m_cfg->BrokerName = "";
	m_cfg->Password = m_password.c_str();
	m_cfg->Pin = m_PIN.c_str();
	m_cfg->CertSocket = -1;
	m_cfg->CertHost = m_SMFrontAddr.c_str();
	m_cfg->CertPort = atoi(m_SMPort.c_str());
	m_cfg->TimeoutMs = 5 * 60 * 1000; //5min

	int rst = m_SMCertSDK_New(m_cfg, m_cert);
	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_New Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_New DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}

}

void SMCertUser::Ctp_SMCertSDK_Free()
{
	int rst =m_SMCertSDK_Free(*m_cert);

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_Free Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_Free DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_CertEnroll()
{
	int rst = m_SMCertSDK_CertEnroll(*m_cert);

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_CertEnroll Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_CertEnroll DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_CertDelay()
{
	int rst = m_SMCertSDK_CertDelay(*m_cert);

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_CertDelay Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_CertDelay DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_CertQuery()
{
	int cert_num = 0;
	const SMCert_t *cert_msg = nullptr;
	int rst = m_SMCertSDK_CertQuery(*m_cert, &cert_msg, &cert_num);

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_CertQuery Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{		
		LOG("SMCertSDK_CertQuery DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		//////////可能用户名下没有过证书/////////
		if (cert_num > 0)
		{			
			for (int i = 0; i < cert_num; i++)
			{
				SMCert_t t = (SMCert_t)cert_msg[i];
				LOG("CertID=%s, UserID=%s, DeviceID=%s, CertInfo=%s, IsCurrent=%d\n", 
					t.CertID, t.UserID, t.DeviceID, t.CertInfo, t.IsCurrent);
			}		
		}
		else
		{
			LOG("User has NO Certificate!!!\n");
		}		
	}
}

void SMCertUser::Ctp_SMCertSDK_CertRevoke()
{
	char *CertID = new char[50];

	cout <<  "请输入证书编号: ";
	cin >> CertID;
	cout << endl;

	int rst = m_SMCertSDK_CertRevoke(*m_cert, CertID);

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_CertRevoke Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_CertRevoke DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}

void SMCertUser::Ctp_SMCertSDK_ResetPin()
{
	string NewPIN;

	cout << "请输入新的PIN码，至少6位: ";
	cin >> NewPIN;
	cout << endl;

	int rst = m_SMCertSDK_ResetPin(*m_cert, NewPIN.c_str());

	if (rst != SMCERTSDK_ERR_NONE)
	{
		LOG("SMCertSDK_ResetPin Error : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
		return;
	}
	else
	{
		LOG("SMCertSDK_ResetPin DONE : 0x%X, %s\n", rst, m_map_errormsg[rst].c_str());
	}
}
