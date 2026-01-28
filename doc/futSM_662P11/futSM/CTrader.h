#pragma once

#include "define.h"
#include "ThostFtdcTraderApi.h"
#include "ThostFtdcUserApiStruct.h"
#include "ThostFtdcUserApiDataType.h"

class CTradeUser : public CThostFtdcTraderSpi
{
public:
	CTradeUser();
	~CTradeUser();

	CThostFtdcTraderApi *CreateFtdcTraderApi(const char *pszFlowPath = "");

	void Init();

	void Release();

	void OnFrontConnected();

	void OnFrontDisconnected(int nReason);

	void OnRspAuthenticate(CThostFtdcRspAuthenticateField *pRspAuthenticateField, CThostFtdcRspInfoField *pRspInfo, int nRequestID, bool bIsLast);

	void ReqUserLoginSM();

	void OnRspUserLogin(CThostFtdcRspUserLoginField *pRspUserLogin, CThostFtdcRspInfoField *pRspInfo, int nRequestID, bool bIsLast);

	void OnRspError(CThostFtdcRspInfoField * pRspInfo, int nRequestID, bool bIsLast);


public:
	CThostFtdcTraderApi *m_pTradeApi;

	string m_smcert;
	string m_brokerid;
	string m_userid;
	string m_password;
	string m_PIN;
	string m_SMFrontAddr;
	string m_SMPort;
	string m_SSLFrontAddr;

	string m_AuthCode;
	string m_AppID;

	HANDLE sem_init = CreateEvent(NULL, false, false, NULL);
	HANDLE sem_ReqAuthenticate = CreateEvent(NULL, false, false, NULL);
	HANDLE sem_ReqUserLoginSM = CreateEvent(NULL, false, false, NULL);
	HANDLE sem_ReqQryClassifiedInstrument = CreateEvent(NULL, false, false, NULL);
	HANDLE sem_ReqUserLogout = CreateEvent(NULL, false, false, NULL);
	HANDLE sem_ReqQryInstrument = CreateEvent(NULL, false, false, NULL);
	int RequestID = 0;
};