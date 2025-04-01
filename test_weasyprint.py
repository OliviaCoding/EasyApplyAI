from weasyprint import HTML

# 生成一个简单的 PDF 测试
HTML(string='<h1>WeasyPrint 测试</h1><p>如果这个 PDF 生成成功，说明 WeasyPrint 安装正确！</p>').write_pdf('test.pdf')
print("✅ PDF 生成成功！检查当前目录下的 test.pdf")
