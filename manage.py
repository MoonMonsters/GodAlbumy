#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by Flynn on 2018-11-06 19:12


from albumy import create_app

app = create_app('production')

if __name__ == '__main__':
	app.run(debug=False)
