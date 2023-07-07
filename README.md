# 基于Snipaste的截图文字识别工具

## 介绍

基于Snipaste的截图文字识别工具，使用飞浆的OCR模型，基于Snipaste的强大截图功能，实现截图文字自动识别。

支持中英文，支持多行文字识别，支持多种截图模式，支持多种识别结果输出方式。

## 使用方法

1. 安装Snipaste
2. 下载release中打包好的文件，或者自行编译安装
3. 运行Snipaste
4. 修改根目录下的config.yaml文件，修改`path`为Snipaste的截图快捷保存目录，修改`modelpath`为OCR模型的路径，不修改则使用项目根目录中的models目录下的模型
5. 运行本程序
6. 截图，按下快捷键`Ctrl+Shift+S`，快捷键为Snipaste默认的自动保存快捷键，即可进行截图文字识别

## 识别结果

识别结果按照截图格式进行输出，部分凌乱的格式支持的不是很好，可以自行尝试修改。
飞浆的模型识别率还是挺高的，如果有特殊文字需求可以自行训练模型，参考：[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)