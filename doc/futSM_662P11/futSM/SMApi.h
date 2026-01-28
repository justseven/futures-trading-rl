#ifndef __CTPSMSDK_H
#define __CTPSMSDK_H
#ifdef __cplusplus
extern "C" {
#endif // __cplusplus
/* SDK 错误码 */
#define SMSDK_ERR_NONE                    0                             /* 成功 */
#define SMSDK_ERR_BASE                    0x0A000000                    /* 错误码 */
#define SMSDK_ERR_FAILED                  (SMSDK_ERR_BASE + 0x0001)     /* 失败 */
#define SMSDK_ERR_LOCALRETRY              (SMSDK_ERR_BASE + 0x0002)     /* 本地主动调用异步接口重试 */

#define SMSDK_ERR_INTERNAL_UNKNOWN        (SMSDK_ERR_BASE + 0x0100)     /* 内部未知错误 */
#define SMSDK_ERR_INTERNAL_GENKEY         (SMSDK_ERR_BASE + 0x0101)     /* 产生密钥对失败 */
#define SMSDK_ERR_INTERNAL_DIGEST         (SMSDK_ERR_BASE + 0x0102)     /* 摘要失败 */
#define SMSDK_ERR_INTERNAL_BASE64         (SMSDK_ERR_BASE + 0x0103)     /* base64编码失败 */
#define SMSDK_ERR_INTERNAL_RANDOM         (SMSDK_ERR_BASE + 0x0104)     /* 产生随机数失败 */
#define SMSDK_ERR_INTERNAL_XTSIGN         (SMSDK_ERR_BASE + 0x0105)     /* 协同签名失败 */

#define SMSDK_ERR_PARAM_NULL              (SMSDK_ERR_BASE + 0x0200)     /* 空参数 */
#define SMSDK_ERR_PARAM_INVALID           (SMSDK_ERR_BASE + 0x0201)     /* 参数非法 */
#define SMSDK_ERR_PARAM_BUFFER_SMALL      (SMSDK_ERR_BASE + 0x0202)     /* 缓冲区太小 */

#define SMSDK_ERR_NETWORK_CONNECT         (SMSDK_ERR_BASE + 0x0300)     /* 连接出错 */
#define SMSDK_ERR_NETWORK_REQUEST         (SMSDK_ERR_BASE + 0x0301)     /* 请求错误 */
#define SMSDK_ERR_NETWORK_RESPONSE        (SMSDK_ERR_BASE + 0x0302)     /* 响应错误 */

#define SMSDK_ERR_STORE_UNKNOWN     (SMSDK_ERR_BASE + 0x0400)     /* 存储未知错误 */
#define SMSDK_ERR_PIN_INCORRECT     (SMSDK_ERR_BASE + 0x0401)     /* PIN 不正确 */
#define SMSDK_ERR_PIN_LOCKED        (SMSDK_ERR_BASE + 0x0402)     /* PIN 已锁定 */
#define SMSDK_ERR_CERT_NOT_EXISTS   (SMSDK_ERR_BASE + 0x0403)     /* 证书不存在 */
#define SMSDK_ERR_CERT_EXPIRED      (SMSDK_ERR_BASE + 0x0404)     /* 证书过期 */
#define SMSDK_ERR_CERT_OVERLIMIT    (SMSDK_ERR_BASE + 0x0405)     /* 证书个数超限 */
#define SMSDK_ERR_CERT_INVALID      (SMSDK_ERR_BASE + 0x0406)     /* 证书无效 */
#define SMSDK_ERR_USER_PASS		    (SMSDK_ERR_BASE + 0x0407)     /* 错误的用户名或密码 */


/* SSL错误码 */
#define SMSSL_ERROR_NONE                  0       /* 操作成功 */
#define SMSSL_ERROR_SSL                   1       /* SSL错误 */
#define SMSSL_ERROR_WANT_READ             2       /* 读阻塞 */
#define SMSSL_ERROR_WANT_WRITE            3       /* 写阻塞 */
#define SMSSL_ERROR_SYSCALL               5       /* 系统中断 */
#define SMSSL_ERROR_ZERO_RETURN           6       /* SSL连接关闭 */
#define SMSSL_ERROR_WANT_CONNECT          7       /* 连接阻塞 */
#define SMSSL_ERROR_WANT_ACCEPT           8       /* 监听阻塞 */

/*
说明：
1. 用户本地证书路径，为用户数据目录下（Windows和Linux都是如此）
如系统登录用户名为UserXXX，证书路径为：
Windows： 
		C:\Users\UserXXX\AppData\Roaming\koal\smkdata （格尔）
		C:\Users\UserXXX\AppData\Roaming\ifs\smidata  （信安）
		C:\Users\UserXXX\AppData\Roaming\syd\smsdata  （信雅达）
Linux： 		  
		/home/UserXXX/koal/smkdata （格尔）
		/home/UserXXX/ifs/smidata （信安）
		/home/UserXXX/syd/smsdata （信雅达）
		  
*/

/* 证书、签名验签配置 */
typedef struct SMUserConfig_s {
    const char  *BrokerID;          /* 用户的 broker id */
    const char  *UserID;            /* 用户的 user id */
	const char  *Pin;				/* 用户的本地PIN码 */
	const char  *Password;			/* 用户的密码，用于用户下证校验 */
	const char  *CertHost;         /* 协同签名服务器地址 */
    int          CertPort;         /* 协同签名服务端端口 */
	int          CertSocket;       /* 协同签名服务socket */
    int          TimeoutMs;         /* 连接超时时间 */
} SMUserConfig_t;

/* SSL配置 */
typedef struct SMSSLConfig_s {
    int          ServerSocket;      /* SSL服务端的socket */
    int          TimeoutMs;         /* 连接超时时间 */
} SMSSLConfig_t;

/* SDK句柄 */
typedef void * SMSDK_t;

/*
 * 返回当前API版本
 *
 * @return const char * 
 */
const char * SMSDK_GetVersion();

/**
 * @brief SDK全局初始化
 *
 * 程序开始运行后，一个进程内，SDK需要且仅需要一次全局初始化
 * 一般用于加载第三方的dll等操作
 * @param LogFile  [in] 错误日志文件（为空则不记录错误日志）
 * @return int	   成功返回 SMSDK_ERR_NONE
 *                 失败返回错误码
 */
int SMSDK_Init(const char *LogFile);

/**
 * @brief SDK全局初始化清理
 *
 * 程序结束运行前，SDK需要且仅需要一次全局初始化的清理
 *
 * @return int  成功返回 SMSDK_ERR_NONE
 *              失败返回错误码
 */
int SMSDK_Clean(void);

/**
 * @brief 创建句柄
 * 
 * 一个句柄只需调用一次
 * 需要绑定一个连接了签名验签服务器的socket
 * 该socket在SSL连接成功或者释放句柄之后，内部不再保存socket，需要外部手动关闭该socket。
 * 
 * @param Config  [in] 用户参数配置
 * @param hSDK    [out] 句柄
 * @return int    成功返回 SMSDK_ERR_NONE
 *                失败返回错误码
 */
int SMSDK_New(const SMUserConfig_t *Config, SMSDK_t *hSDK);

/**
 * @brief 释放句柄
 *
 * 释放SDK句柄。
 *
 * @param hSDK  [in] SDK句柄
 * @return int  成功返回 SMSDK_ERR_NONE
 *              失败返回错误码
 */
int SMSDK_Free(SMSDK_t hSDK);


/**
 * @brief 证书校验：校验PIN码、协同签名校验私钥等；
 *
 * 该接口为非阻塞调用,由外部线程监控协同签名socket的读写事件驱动调用
 * 网络IO阻塞时返回 SMSSL_ERROR_WANT_READ/SMSSL_ERROR_WANT_WRITE
 * 返回SMSDK_ERR_LOCALRETRY，表示需要主动再次调用该接口，不等待网络IO（避免其他用户同时在写本地证书）
 *
 * 流程描述：
 * 1）检查本地是否有证书；
 *		无：返回SMSDK_ERR_CERT_NOT_EXISTS；
 *			客户端调用SMCertApi的SMCertSDK_CertEnroll，重新申请证书
 *		有：继续2）
 * 2) 校验PIN；
 *    失败：返回SMSDK_ERR_PIN_INCORRECT；PIN校验错超过10次，锁定PIN码，返回SMSDK_ERR_PIN_LOCKED
 *			SMSDK_ERR_PIN_INCORRECT：客户端提示用户PIN码错误；
 *			SMSDK_ERR_PIN_LOCKED： 客户端提示用户，联系管理员处理；管理员删除服务端证书；或者指导用户，删除本地证书后重试登录。
 *    成功：继续3）
 * 3) 检查证书状态：
 *	  无效：证书过期，返回SMSDK_ERR_CERT_EXPIRED；证书无效，返回SMSDK_ERR_CERT_INVALID
 *	   	    客户端调用SMCertApi的SMCertSDK_CertDelay，更新证书
 *    有效：继续4）
 * 4）协同签名校验私钥等；
 *    失败：返回SMSDK_ERR_INTERNAL开头的错误码，或SMSDK_ERR_CERT_INVALID
 *			客户端调用SMCertApi的SMCertSDK_CertDelay，更新证书
 *    成功：返回SMSDK_ERR_NONE
 *
 * @param hSDK  [in] SDK句柄
 * @return int  成功返回 SMSDK_ERR_NONE
 *              网络IO阻塞返回 SMSSL_ERROR_WANT_READ/SMSSL_ERROR_WANT_WRITE
 *				本地IO阻塞返回 SMSDK_ERR_LOCALRETRY
 *              证书校验错误，返回SMSDK_ERR_CERT_NOT_EXISTS | SMSDK_ERR_CERT_EXPIRED | SMSDK_ERR_CERT_INVALID
 *              PIN校验错，返回SMSDK_ERR_PIN_INCORRECT；PIN校验错超过10	次，锁定PIN码，返回SMSDK_ERR_PIN_LOCKED
 *              失败返回错误码
 */
int SMSDK_CertVerify(SMSDK_t hSDK);


/**
 * @brief 连接SSL
 *
 * 该接口为非阻塞调用
 * 
 * 网络IO阻塞时返回 SMSSL_ERROR_WANT_READ/SMSSL_ERROR_WANT_WRITE
 * 返回SMSSL_ERROR_WANT_READ，表示需将返回的Socket挂载到网络IO读事件队列
 * 返回SMSSL_ERROR_WANT_WRITE，表示需将返回的Socket挂载到网络IO写事件队列				 
 *
 * 本地IO阻塞返回 SMSDK_ERR_LOCALRETRY （本地证书文件被锁的情况）
 *
 * @param hSDK        [in] SDK句柄
 * @param Config      [in] SSL相关配置
 * @param Socket      [out] 返回需要监听的socket
 * @return int        成功返回 SMSDK_ERR_NONE
 *                    网络IO阻塞时返回 SMSSL_ERROR_WANT_READ/SMSSL_ERROR_WANT_WRITE
 *					  本地IO阻塞返回   SMSDK_ERR_LOCALRETRY 
 *                    失败返回错误码
 */
int SMSDK_SSLConnect(SMSDK_t hSDK, const SMSSLConfig_t *Config, int *Socket);

/**
 * @brief 断开SSL
 *
 * 断开SSL连接
 *
 * @param hSDK  [in] SDK句柄
 * @return int  成功返回 SMSDK_ERR_NONE
 *              失败返回错误码
 */
int SMSDK_SSLShutdown(SMSDK_t hSDK);

/**
 * @brief 写入SSL数据
 *
 * 写入数据
 *
 * @param hSDK     [in] SDK句柄
 * @param Buf      [in] 写入数据缓冲区
 * @param Len      [in] 预计加密长度 [out] 实际加密的长度
 * @return int     成功返回 SMSDK_ERR_NONE
 *				   网络IO阻塞返回SMSSL_ERROR_WANT_READ/SMSSL_ERROR_WANT_WRITE
 *                 失败返回错误码
 */
int SMSDK_SSLWrite(SMSDK_t hSDK, const void *Buf, int *Len);

/**
 * @brief 读取SSL数据
 *
 * 读取数据
 *
 * 注：读取数据后需要调用SMSDK_SSLPending()检查数据是否已读取完成，
 * 若存在未读数据，则需要立即调用本接口继续读取数据。
 *
 * @param hSDK     [in] SDK句柄
 * @param Buf      [out] 读取数据缓冲区
 * @param Len      [in] 缓冲区大小 [out] 读取数据长度
 * @return int     成功返回 SMSDK_ERR_NONE
 *				   网络IO阻塞时返回 SMSSL_ERROR_WANT_READ
 *                 失败返回错误码
 */
int SMSDK_SSLRead(SMSDK_t hSDK, void *Buf, int *Len);

/**
 * @brief 获取句柄缓冲区未读数据长度
 *
 * 该接口需要在调用SMSDK_SSLRead()后调用，返回剩余未读数据长度。
 *
 * @param hSDK  [in] SDK句柄
 * @param Len   [out] 未读数据长度
 * @return int
 */
int SMSDK_SSLPending(SMSDK_t hSDK, int *Len);

/**
 * @brief 获取客户端通信地址
 *
 * 获取客户端通信的真实IP地址，IP内容可能为IPv4或IPv6
 * 返回IPv6应为未压缩过的地址，如：fe8000000000000000000000004:39984
 * 返回格式：IP:PORT
 * 使用场景：客户端通过NAT后与网关通信，可获取最终与网关通信的真实客户端IP
 *
 * @param hSDK  [in] SDK句柄
 * @param IP    [out] IP缓冲区
 * @param Len   [in] 缓冲区大小 [out] IP长度
 * @return int
 */
int SMSDK_SSLClientIP(SMSDK_t hSDK, char *IP, int *Len);

#ifdef __cplusplus
}
#endif // __cplusplus
#endif // __CTPSMSDK_H
