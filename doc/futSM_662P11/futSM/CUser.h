#pragma once

#include "SMApi.h"
#include "SMCertApi.h"
#include <windows.h>
#include <stdio.h>
#include <iostream>
#include "define.h"

typedef const char *(*SM_GetVersion)(void);
typedef int(*SM_Init)(const char *LogFile);
typedef int(*SM_Clean)(void);
typedef int(*SM_New)(const SMCertUserConfig_t *Config, SMCertSDK_t *hSDK);
typedef int(*SM_Free)(SMCertSDK_t hSDK);
typedef int(*SM_CertQuery)(SMCertSDK_t hSDK, const SMCert_t **pCert, int *total);
typedef int(*SM_CertEnroll)(SMCertSDK_t hSDK);
typedef int(*SM_CertDelay)(SMCertSDK_t hSDK);
typedef int(*SM_CertRevoke)(SMCertSDK_t hSDK, const char *CertID);
typedef int(*SM_ResetPin)(SMCertSDK_t hSDK, const char *NewPIN);


class SMCertUser
{
public:
	SMCertUser();
	~SMCertUser();

public:

	//加载SMapi动态库
	void Ctp_LoadAPI();

	//返回当前API版本
	void Ctp_SMCertSDK_GetVersion();

	//api全局初始化
	void Ctp_SMCertSDK_Init();

	//SDK全局初始化清理
	void Ctp_SMCertSDK_Clean();

	//创建句柄
	void Ctp_SMCertSDK_New();

	//释放句柄
	void Ctp_SMCertSDK_Free();

	//申请用户证书，并设置用户PIN码，PIN码长度不能小于6位
	void Ctp_SMCertSDK_CertEnroll();

	//延期本设备用户证书
	void Ctp_SMCertSDK_CertDelay();

	//查询用户服务端所有有效的证书信息，已过期或已作废的证书不返回；
	void Ctp_SMCertSDK_CertQuery();

	//废弃用户证书
	void Ctp_SMCertSDK_CertRevoke();

	//重置PIN
	void Ctp_SMCertSDK_ResetPin();


public:
	string m_smcert;
	string m_brokerid;
	string m_userid;
	string m_password;
	string m_PIN;
	string m_SMFrontAddr;
	string m_SMPort;
	string m_SSLFrontAddr;

	HMODULE m_hLib;

	SM_GetVersion m_SMCertSDK_Version;
	SM_Init m_SMCertSDK_Init;
	SM_Clean m_SMCertSDK_Clean;
	SM_New m_SMCertSDK_New;
	SM_Free m_SMCertSDK_Free;
	SM_CertQuery m_SMCertSDK_CertQuery;
	SM_CertEnroll m_SMCertSDK_CertEnroll;
	SM_CertDelay m_SMCertSDK_CertDelay;
	SM_CertRevoke m_SMCertSDK_CertRevoke;
	SM_ResetPin m_SMCertSDK_ResetPin;

	SMCertSDK_t *m_cert;
	SMCertUserConfig_t *m_cfg;
	map<int64_t, string> m_map_errormsg;

};
