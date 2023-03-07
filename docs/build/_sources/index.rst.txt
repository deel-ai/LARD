.. Lard documentation master file, created by
   sphinx-quickstart on Tue Mar  7 09:37:35 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Lard's documentation!
================================

.. image:: ../assets/Lard_grey.png
   :width: 600

This documentation contains the prototypes and technical descriptions of the python code realized for dataset generation
and export.

For information about its usage, please refer instead to the ``Readme.md`` file in the project root directory.


.. toctree::
   :maxdepth: 2
   :caption: Contents:



Technical documentation
=======================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Documentation generation and update
===================================

How to modify or generate new documentations (here using Sphinx in the Pycharm IDE):

- Installation :

   - Ensure that ``Insert documentation comment stub`` is selected in ``Editor | General | Smart Keys``.
   - In ``Smart Keys | Python``, check ``Insert type placeholders in the documentation comment stub``
   - In ``Tools | Python Integrated Tools``, ensures ``Docstring format`` is ``restructured``
   - Install sphinx :

   .. code-block:: console

      pip install sphinx
      pip install sphinx-rtd-theme

- To modify/rebuild the documentation :

   - In ``./docs``, run in the terminal :

   .. code-block:: console

         sphinx-apidoc --module-first -o ./source ..

   - In Edit Configuration : create sphinx task, input is ``docs/source``, ouput is ``docs/build``, working directory is ``docs/source``
   - Run the previously created task when you have finished to modify the documentation strings in the project source code.