#include <iostream>
#include "CUser.h"
#include "define.h"
#include "CTrader.h"

using namespace std;

const char *DEMO_VERSION = "v1.0.5";

void menu()
{
	cout << "\n\n1.申请用户证书" << endl;
	cout << "2.延期用户证书" << endl;
	cout << "3.废弃用户证书" << endl;
	cout << "4.查询用户证书" << endl;
	cout << "5.重置PIN码" << endl;
	cout << "6.查看商密api版本号" << endl;
	cout << "7.商密登录" << endl;
	cout << "100.退出\n" << endl;
	cout << "请选择操作代码: ";
}

int main(int argc, char *argv[])
{	
	logfile = fopen("out.log", "w");

	LOG("------DEMO Version ：%s------\n", DEMO_VERSION);
	LOG("------Current Tradeapi Verion ：%s------\n", CThostFtdcTraderApi::GetApiVersion());
	
	int _i_switch_flag = 0;
	bool _b_start = true;
	SMCertUser ss;
	ss.Ctp_LoadAPI();
	ss.Ctp_SMCertSDK_GetVersion();
	ss.Ctp_SMCertSDK_Init();
	ss.Ctp_SMCertSDK_New();

	while (_b_start)
	{
		menu();
		cin >> _i_switch_flag;
		switch (_i_switch_flag)
		{
		case 1:
		{
			ss.Ctp_SMCertSDK_CertEnroll();
			break;
		}
		case 2:
		{
			ss.Ctp_SMCertSDK_CertDelay();
			break;
		}
		case 3:
		{
			ss.Ctp_SMCertSDK_CertRevoke();
			break;
		}
		case 4:
		{
			ss.Ctp_SMCertSDK_CertQuery();
			break;
		}
		case 5:
		{
			ss.Ctp_SMCertSDK_ResetPin();
			break;
		}
		case 6:
		{
			ss.Ctp_SMCertSDK_GetVersion();
			break;
		}
		case 7:
		{
			CTradeUser pp;
			pp.Init();
			pp.ReqUserLoginSM();
			break;
		}
		case 100:
		{
			_b_start = false;
			break;
		}
		default:
			cout << "无此选项，即将退出！！！" << endl;
			_b_start = false;
			break;
		}

	}
	
	////结束程序运行////
	ss.Ctp_SMCertSDK_Free();
	ss.Ctp_SMCertSDK_Clean();

	//cin.ignore();
	//cin.get();
}