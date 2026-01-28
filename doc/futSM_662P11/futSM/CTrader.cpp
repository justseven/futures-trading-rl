#include "CTrader.h"

CTradeUser::CTradeUser()
{
	m_smcert = getConfig("config", "SMCert");
	m_brokerid = getConfig("config", "BrokerID");
	m_userid = getConfig("config", "UserID");
	m_password = getConfig("config", "Password");
	m_PIN = getConfig("config", "PIN");
	m_SMFrontAddr = getConfig("config", "SMFrontAddr");
	m_SMPort = getConfig("config", "SMPort");
	m_SSLFrontAddr = getConfig("config", "SSLFrontAddr");
	m_AuthCode = getConfig("config", "AuthCode");
	m_AppID = getConfig("config", "AppID");
}

CTradeUser::~CTradeUser()
{

}

CThostFtdcTraderApi * CTradeUser::CreateFtdcTraderApi(const char * pszFlowPath)
{
	return m_pTradeApi = CTradeUser::CreateFtdcTraderApi(pszFlowPath);
}

void CTradeUser::Init()
{
	m_pTradeApi = CThostFtdcTraderApi::CreateFtdcTraderApi(".//flow/");
	string _s_FrontAddr = m_smcert + "://" + m_SMFrontAddr + ":" + m_SMPort + "/" + m_SSLFrontAddr;
	m_pTradeApi->RegisterSpi(this);
	m_pTradeApi->RegisterFront(const_cast<char *>(_s_FrontAddr.c_str()));
	m_pTradeApi->SubscribePrivateTopic(THOST_TERT_QUICK);
	m_pTradeApi->SubscribePublicTopic(THOST_TERT_QUICK);
	LOG("<RegisterFront> <%s>\n", _s_FrontAddr.c_str());
	LOG("<Init>\n");
	LOG("<\Init>.\n");
	m_pTradeApi->Init();
	WaitForSingleObject(sem_init, INFINITE);

}

void CTradeUser::Release()
{
	m_pTradeApi->Release();
}

void CTradeUser::OnFrontConnected()
{
	LOG("<OnFrontConnected>.\n");
	LOG("<\OnFrontConnected>.\n");
	SetEvent(sem_init);
}

void CTradeUser::OnFrontDisconnected(int nReason)
{
	LOG("<OnFrontDisconnected>.\n");
	LOG("   [nReason] [%d]\n", nReason);
	LOG("<\OnFrontDisconnected>.\n");
	SetEvent(sem_ReqUserLoginSM);
}

void CTradeUser::OnRspAuthenticate(CThostFtdcRspAuthenticateField * pRspAuthenticateField, CThostFtdcRspInfoField * pRspInfo, int nRequestID, bool bIsLast)
{
	LOG("<OnRspAuthenticate>\n");
	if (pRspAuthenticateField)
	{
		LOG("\tBrokerID [%s]\n", pRspAuthenticateField->BrokerID);
		LOG("\tUserID [%s]\n", pRspAuthenticateField->UserID);
		LOG("\tUserProductInfo [%s]\n", pRspAuthenticateField->UserProductInfo);
		LOG("\tAppID [%s]\n", pRspAuthenticateField->AppID);
		LOG("\tAppType [%c]\n", pRspAuthenticateField->AppType);
	}
	if (pRspInfo)
	{
		LOG("\tErrorMsg [%s]\n", pRspInfo->ErrorMsg);
		LOG("\tErrorID [%d]\n", pRspInfo->ErrorID);
	}
	LOG("\tnRequestID [%d]\n", nRequestID);
	LOG("\tbIsLast [%d]\n", bIsLast);
	LOG("</OnRspAuthenticate>\n");
	//SetEvent(sem_ReqAuthenticate);
}

void CTradeUser::ReqUserLoginSM()
{
	LOG("\n====ReqUserLoginSM====..\n");
	CThostFtdcReqUserLoginSMField *pReqUserLoginSM = new CThostFtdcReqUserLoginSMField;
	memset(pReqUserLoginSM, 0, sizeof(CThostFtdcReqUserLoginSMField));

	strcpy(pReqUserLoginSM->BrokerID, m_brokerid.c_str());
	strcpy(pReqUserLoginSM->UserID, m_userid.c_str());
	strcpy(pReqUserLoginSM->BrokerName, "");
	strcpy(pReqUserLoginSM->Password, m_password.c_str());
	strcpy(pReqUserLoginSM->PIN, m_PIN.c_str());
	strcpy(pReqUserLoginSM->AppID, m_AppID.c_str());
	strcpy(pReqUserLoginSM->AuthCode, m_AuthCode.c_str());	

	LOG("<ReqUserLoginSM>\n");
	LOG("\tTradingDay [%s]\n", pReqUserLoginSM->TradingDay);
	LOG("\tBrokerID [%s]\n", pReqUserLoginSM->BrokerID);
	LOG("\tBrokerName [%s]\n", pReqUserLoginSM->BrokerID);
	LOG("\tUserID [%s]\n", pReqUserLoginSM->UserID);
	LOG("\tPassword [%s]\n", pReqUserLoginSM->Password);
	LOG("\tUserProductInfo [%s]\n", pReqUserLoginSM->UserProductInfo);
	LOG("\tInterfaceProductInfo [%s]\n", pReqUserLoginSM->InterfaceProductInfo);
	LOG("\tProtocolInfo [%s]\n", pReqUserLoginSM->ProtocolInfo);
	LOG("\tMacAddress [%s]\n", pReqUserLoginSM->MacAddress);
	LOG("\tOneTimePassword [%s]\n", pReqUserLoginSM->OneTimePassword);
	LOG("\tClientIPAddress [%s]\n", pReqUserLoginSM->ClientIPAddress);
	LOG("\tLoginRemark [%s]\n", pReqUserLoginSM->LoginRemark);
	LOG("\tAuthCode [%s]\n", pReqUserLoginSM->AuthCode);
	LOG("\tAppID [%s]\n", pReqUserLoginSM->AppID);
	LOG("\tPIN [%s]\n", pReqUserLoginSM->PIN);
	LOG("\tClientIPPort [%d]\n", pReqUserLoginSM->ClientIPPort);
	LOG("</ReqUserLoginSM>\n");

	int t = m_pTradeApi->ReqUserLoginSM(pReqUserLoginSM, RequestID++);
	LOG((t == 0) ? "客户端登录请求...成功[%d]\n" : "客户端登录请求...失败=[%d]\n", t);
	WaitForSingleObject(sem_ReqUserLoginSM, INFINITE);
	Sleep(1000);
}

void CTradeUser::OnRspUserLogin(CThostFtdcRspUserLoginField* pRspUserLogin, CThostFtdcRspInfoField* pRspInfo, int nRequestID, bool bIsLast)
{
	LOG("<OnRspUserLogin>\n");
	if (pRspUserLogin)
	{
		LOG("\tTradingDay [%s]\n", pRspUserLogin->TradingDay);
		LOG("\tLoginTime [%s]\n", pRspUserLogin->LoginTime);
		LOG("\tBrokerID [%s]\n", pRspUserLogin->BrokerID);
		LOG("\tUserID [%s]\n", pRspUserLogin->UserID);
		LOG("\tSystemName [%s]\n", pRspUserLogin->SystemName);
		LOG("\tMaxOrderRef [%s]\n", pRspUserLogin->MaxOrderRef);
		LOG("\tSHFETime [%s]\n", pRspUserLogin->SHFETime);
		LOG("\tDCETime [%s]\n", pRspUserLogin->DCETime);
		LOG("\tCZCETime [%s]\n", pRspUserLogin->CZCETime);
		LOG("\tFFEXTime [%s]\n", pRspUserLogin->FFEXTime);
		LOG("\tINETime [%s]\n", pRspUserLogin->INETime);
		LOG("\tFrontID [%d]\n", pRspUserLogin->FrontID);
		LOG("\tSessionID [%d]\n", pRspUserLogin->SessionID);
	}
	if (pRspInfo)
	{
		LOG("\tErrorMsg [%s]\n", pRspInfo->ErrorMsg);
		LOG("\tErrorID [%d]\n", pRspInfo->ErrorID);
	}
	LOG("\tnRequestID [%d]\n", nRequestID);
	LOG("\tbIsLast [%d]\n", bIsLast);
	LOG("</OnRspUserLogin>\n");
	SetEvent(sem_ReqUserLoginSM);
	
}

void CTradeUser::OnRspError(CThostFtdcRspInfoField * pRspInfo, int nRequestID, bool bIsLast)
{
	LOG("<OnRspError>\n");
	if (pRspInfo)
	{
		LOG("\tErrorMsg [%s]\n", pRspInfo->ErrorMsg);
		LOG("\tErrorID [%d]\n", pRspInfo->ErrorID);
	}
	LOG("\tnRequestID [%d]\n", nRequestID);
	LOG("\tbIsLast [%d]\n", bIsLast);
	LOG("</OnRspError>\n");
	SetEvent(sem_ReqUserLoginSM);
	
};